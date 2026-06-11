import csv
import io
import os
import sqlite3
import unicodedata
from datetime import datetime, date
from functools import wraps
from typing import Any, Dict, List

from PIL import Image

from flask import (
    Flask,
    Response,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.environ.get("DATA_DIR", os.path.join(BASE_DIR, "data"))
os.makedirs(DATA_DIR, exist_ok=True)
DATABASE = os.environ.get("DATABASE_PATH", os.path.join(DATA_DIR, "eco_recicle.sqlite3"))

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "troque-essa-chave-no-coolify")

DEFAULT_MATERIALS = [
    ("Papelão", 0.30),
    ("Papel", 0.20),
    ("Filme", 0.30),
    ("Plástico duro", 0.10),
    ("Pet", 0.50),
    ("Alumínio", 8.00),
    ("Metal", 18.00),
    ("Cobre", 40.00),
    ("Fiação de cobre", 15.00),
    ("Ferro", 0.30),
    ("Bateria", 2.00),
]


def money(value: float | int | None) -> str:
    value = float(value or 0)
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def kg(value: float | int | None) -> str:
    value = float(value or 0)
    return f"{value:,.3f}".replace(",", "X").replace(".", ",").replace("X", ".")


def br_datetime(value: str | None) -> str:
    if not value:
        return ""
    try:
        dt = datetime.fromisoformat(value)
        return dt.strftime("%d/%m/%Y %H:%M")
    except ValueError:
        return value


def br_date(value: str | None) -> str:
    if not value:
        return ""
    try:
        return datetime.strptime(value, "%Y-%m-%d").strftime("%d/%m/%Y")
    except ValueError:
        return value





# PDF térmico simples gerado no servidor para o iPhone reconhecer como arquivo PDF real.
def _pdf_clean(value: Any) -> str:
    """Deixa o texto seguro para PDF térmico/iPhone, evitando letras quebradas como ALUM�NIO."""
    text = str(value or "")
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return text


def _pdf_escape(value: Any) -> str:
    text = _pdf_clean(value)
    text = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    return text


def _wrap_pdf_text(text: str, max_chars: int = 34) -> list[str]:
    text = _pdf_clean(text)
    words = text.split()
    if not words:
        return [""]
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        if len(current) + 1 + len(word) <= max_chars:
            current += " " + word
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


_LOGO_PDF_CACHE: tuple[int, int, bytes] | None = None

def _load_logo_pdf_image() -> tuple[int, int, bytes] | None:
    """Carrega a logo em JPEG RGB para embutir no PDF térmico."""
    global _LOGO_PDF_CACHE
    if _LOGO_PDF_CACHE is not None:
        return _LOGO_PDF_CACHE

    logo_path = os.path.join(BASE_DIR, "static", "logo.png")
    if not os.path.exists(logo_path):
        return None

    try:
        with Image.open(logo_path) as img:
            img = img.convert("RGBA")
            bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
            bg.alpha_composite(img)
            rgb = bg.convert("RGB")
            buf = io.BytesIO()
            rgb.save(buf, format="JPEG", quality=92, optimize=True)
            _LOGO_PDF_CACHE = (rgb.width, rgb.height, buf.getvalue())
            return _LOGO_PDF_CACHE
    except Exception:
        return None


def _thermal_pdf_response(title: str, meta: list[tuple[str, str]], item_rows: list[tuple[str, str, str]], totals: list[tuple[str, str]], notes: str | None, filename: str) -> Response:
    """
    PDF em formato de recibo térmico, compacto e com a logo da empresa no topo.
    Largura: 58mm, padrão comum de mini impressoras.
    Altura: automática conforme a quantidade de itens, para não cortar nem sobrepor textos.
    """
    width = 58 / 25.4 * 72
    margin = 9
    usable_width = width - (margin * 2)
    ops: list[tuple[str, Any]] = []

    logo_info = _load_logo_pdf_image()
    logo_draw_width = 0.0
    logo_draw_height = 0.0
    if logo_info:
        logo_w_px, logo_h_px, _ = logo_info
        logo_draw_width = min(usable_width * 0.82, 110)
        logo_draw_height = logo_draw_width * (logo_h_px / logo_w_px)

    cursor = 10.0
    if logo_info:
        logo_x = (width - logo_draw_width) / 2
        ops.append(("image", cursor, logo_x, logo_draw_width, logo_draw_height))
        cursor += logo_draw_height + 6

    def add_text(txt: str, size: int = 7, bold: bool = False, x: float | None = None, align: str = "left", leading: float | None = None):
        nonlocal cursor
        txt = _pdf_clean(txt)
        if x is None:
            if align == "center":
                x = max(margin, (width - (len(txt) * size * 0.46)) / 2)
            elif align == "right":
                x = max(margin, width - margin - (len(txt) * size * 0.48))
            else:
                x = margin
        ops.append(("text", cursor, x, txt, size, bold))
        cursor += leading if leading is not None else size + 2

    def add_line(extra_before: float = 2, extra_after: float = 5):
        nonlocal cursor
        cursor += extra_before
        ops.append(("line", cursor))
        cursor += extra_after

    add_text("ECO RECICLE", 10, True, align="center", leading=12)
    add_text(title.upper(), 8, True, align="center", leading=10)
    add_line(1, 5)

    for label, value in meta:
        for part in _wrap_pdf_text(f"{label}: {value}", 32):
            add_text(part, 7, False, leading=9)

    add_line(2, 5)

    for name, calc, value in item_rows:
        for part in _wrap_pdf_text(name.upper(), 25):
            add_text(part, 8, True, leading=10)
        add_text(calc, 6, False, leading=8)
        add_text(value, 8, True, align="right", leading=10)
        cursor += 2

    add_line(1, 5)

    for label, value in totals:
        line = f"{label}: {value}"
        for part in _wrap_pdf_text(line, 30):
            add_text(part, 8, True, leading=10)

    if notes:
        add_line(1, 5)
        for part in _wrap_pdf_text(f"Obs.: {notes}", 32):
            add_text(part, 6, False, leading=8)

    add_line(2, 5)
    add_text("Obrigado pela preferencia!", 7, True, align="center", leading=9)
    add_text("Sistema Eco Recicle", 5, False, align="center", leading=7)

    min_height = 70 / 25.4 * 72
    height = max(min_height, cursor + 10)

    commands: list[str] = []
    for op in ops:
        if op[0] == "image":
            _, y_from_top, x, img_w, img_h = op
            y = height - y_from_top - img_h
            commands.append(f"q\n{img_w:.2f} 0 0 {img_h:.2f} {x:.2f} {y:.2f} cm\n/Im0 Do\nQ")
        elif op[0] == "text":
            _, y_from_top, x, txt, size, bold = op
            y = height - y_from_top
            font = "F2" if bold else "F1"
            commands.append(f"BT /{font} {size} Tf {x:.2f} {y:.2f} Td ({_pdf_escape(txt)}) Tj ET")
        elif op[0] == "line":
            _, y_from_top = op
            y = height - y_from_top
            commands.append(f"{margin:.2f} {y:.2f} m {width - margin:.2f} {y:.2f} l S")

    content = "\n".join(commands).encode("ascii", "replace")

    objects = [
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n",
    ]

    page_resources = "<< /Font << /F1 4 0 R /F2 5 0 R >>"
    next_obj_num = 6
    logo_obj_num = None
    if logo_info:
        page_resources += f" /XObject << /Im0 {next_obj_num} 0 R >>"
        logo_obj_num = next_obj_num
        next_obj_num += 1
    page_resources += " >>"

    objects.append(
        f"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {width:.2f} {height:.2f}] /Resources {page_resources} /Contents {next_obj_num} 0 R >>\nendobj\n".encode()
    )
    objects.append(b"4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n")
    objects.append(b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>\nendobj\n")

    if logo_info and logo_obj_num is not None:
        img_w_px, img_h_px, img_bytes = logo_info
        objects.append(
            f"{logo_obj_num} 0 obj\n<< /Type /XObject /Subtype /Image /Width {img_w_px} /Height {img_h_px} /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length {len(img_bytes)} >>\nstream\n".encode()
            + img_bytes
            + b"\nendstream\nendobj\n"
        )

    objects.append(
        f"{next_obj_num} 0 obj\n<< /Length {len(content)} >>\nstream\n".encode()
        + content
        + b"\nendstream\nendobj\n"
    )

    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for obj in objects:
        offsets.append(len(pdf))
        pdf.extend(obj)
    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {len(objects)+1}\n0000000000 65535 f \n".encode())
    for off in offsets[1:]:
        pdf.extend(f"{off:010d} 00000 n \n".encode())
    pdf.extend(f"trailer\n<< /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF".encode())

    headers = {
        "Content-Type": "application/pdf",
        "Content-Disposition": f'inline; filename="{filename}"',
        "Cache-Control": "no-store, max-age=0",
        "X-Content-Type-Options": "nosniff",
    }
    return Response(bytes(pdf), headers=headers)


app.jinja_env.filters["money"] = money
app.jinja_env.filters["kg"] = kg
app.jinja_env.filters["br_datetime"] = br_datetime
app.jinja_env.filters["br_date"] = br_date


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_exc: Exception | None = None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db() -> None:
    db = get_db()
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS materials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            price_per_kg REAL NOT NULL DEFAULT 0,
            sale_price_per_kg REAL NOT NULL DEFAULT 0,
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS people (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT,
            doc TEXT,
            address TEXT,
            kind TEXT NOT NULL DEFAULT 'fornecedor',
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS purchases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_id INTEGER,
            person_name_snapshot TEXT NOT NULL,
            purchase_date TEXT NOT NULL,
            notes TEXT,
            payment_method TEXT DEFAULT 'Não informado',
            total_kg REAL NOT NULL DEFAULT 0,
            total_amount REAL NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            FOREIGN KEY(person_id) REFERENCES people(id)
        );

        CREATE TABLE IF NOT EXISTS purchase_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            purchase_id INTEGER NOT NULL,
            material_id INTEGER,
            material_name_snapshot TEXT NOT NULL,
            weight_kg REAL NOT NULL DEFAULT 0,
            price_per_kg REAL NOT NULL DEFAULT 0,
            subtotal REAL NOT NULL DEFAULT 0,
            FOREIGN KEY(purchase_id) REFERENCES purchases(id) ON DELETE CASCADE,
            FOREIGN KEY(material_id) REFERENCES materials(id)
        );

        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_id INTEGER,
            buyer_name_snapshot TEXT NOT NULL,
            sale_date TEXT NOT NULL,
            notes TEXT,
            payment_method TEXT DEFAULT 'Não informado',
            total_kg REAL NOT NULL DEFAULT 0,
            total_amount REAL NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            FOREIGN KEY(person_id) REFERENCES people(id)
        );

        CREATE TABLE IF NOT EXISTS sale_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sale_id INTEGER NOT NULL,
            material_id INTEGER,
            material_name_snapshot TEXT NOT NULL,
            weight_kg REAL NOT NULL DEFAULT 0,
            price_per_kg REAL NOT NULL DEFAULT 0,
            subtotal REAL NOT NULL DEFAULT 0,
            FOREIGN KEY(sale_id) REFERENCES sales(id) ON DELETE CASCADE,
            FOREIGN KEY(material_id) REFERENCES materials(id)
        );
        """
    )

    # Migração simples para bancos que já estavam rodando antes da tela de venda.
    material_columns = {row["name"] for row in db.execute("PRAGMA table_info(materials)").fetchall()}
    if "sale_price_per_kg" not in material_columns:
        db.execute("ALTER TABLE materials ADD COLUMN sale_price_per_kg REAL NOT NULL DEFAULT 0")
        db.execute("UPDATE materials SET sale_price_per_kg = price_per_kg WHERE sale_price_per_kg = 0")

    purchase_columns = {row["name"] for row in db.execute("PRAGMA table_info(purchases)").fetchall()}
    if "payment_method" not in purchase_columns:
        db.execute("ALTER TABLE purchases ADD COLUMN payment_method TEXT DEFAULT 'Não informado'")

    sale_columns = {row["name"] for row in db.execute("PRAGMA table_info(sales)").fetchall()}
    if "payment_method" not in sale_columns:
        db.execute("ALTER TABLE sales ADD COLUMN payment_method TEXT DEFAULT 'Não informado'")

    # Usuário inicial configurável por variável ambiente.
    admin_user = os.environ.get("ADMIN_USER", "admin")
    admin_password = os.environ.get("ADMIN_PASSWORD", "123456")
    exists = db.execute("SELECT id FROM users WHERE username = ?", (admin_user,)).fetchone()
    if not exists:
        db.execute(
            "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
            (admin_user, generate_password_hash(admin_password), datetime.now().isoformat(timespec="seconds")),
        )

    for name, price in DEFAULT_MATERIALS:
        db.execute(
            "INSERT OR IGNORE INTO materials (name, price_per_kg, sale_price_per_kg, active, created_at) VALUES (?, ?, ?, 1, ?)",
            (name, price, price, datetime.now().isoformat(timespec="seconds")),
        )
    db.commit()


@app.before_request
def ensure_db() -> None:
    init_db()


def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("login"))
        return func(*args, **kwargs)
    return wrapper


def get_stock_rows(db: sqlite3.Connection, limit: int | None = None) -> List[sqlite3.Row]:
    limit_sql = "" if limit is None else f"LIMIT {int(limit)}"
    return db.execute(
        f"""
        SELECT
            m.id,
            m.name,
            m.price_per_kg,
            COALESCE(NULLIF(m.sale_price_per_kg, 0), m.price_per_kg) AS sale_price_per_kg,
            COALESCE(p.kg, 0) AS bought_kg,
            COALESCE(p.valor, 0) AS paid_amount,
            COALESCE(s.kg, 0) AS sold_kg,
            COALESCE(s.valor, 0) AS received_amount,
            ROUND(COALESCE(p.kg, 0) - COALESCE(s.kg, 0), 3) AS stock_kg,
            CASE WHEN COALESCE(p.kg, 0) > 0 THEN COALESCE(p.valor, 0) / p.kg ELSE m.price_per_kg END AS avg_cost,
            ROUND((COALESCE(p.kg, 0) - COALESCE(s.kg, 0)) * COALESCE(NULLIF(m.sale_price_per_kg, 0), m.price_per_kg), 2) AS stock_sale_value
        FROM materials m
        LEFT JOIN (
            SELECT material_id, SUM(weight_kg) AS kg, SUM(subtotal) AS valor
            FROM purchase_items
            GROUP BY material_id
        ) p ON p.material_id = m.id
        LEFT JOIN (
            SELECT material_id, SUM(weight_kg) AS kg, SUM(subtotal) AS valor
            FROM sale_items
            GROUP BY material_id
        ) s ON s.material_id = m.id
        WHERE m.active = 1 OR COALESCE(p.kg, 0) > 0 OR COALESCE(s.kg, 0) > 0
        ORDER BY stock_kg DESC, m.name
        {limit_sql}
        """
    ).fetchall()


def stock_totals(rows: List[sqlite3.Row]) -> Dict[str, float]:
    positive_rows = [row for row in rows if (row["stock_kg"] or 0) > 0]
    return {
        "kg": round(sum(float(row["stock_kg"] or 0) for row in positive_rows), 3),
        "value": round(sum(float(row["stock_sale_value"] or 0) for row in positive_rows), 2),
        "negative": sum(1 for row in rows if (row["stock_kg"] or 0) < 0),
    }


@app.context_processor
def inject_globals() -> Dict[str, Any]:
    return {
        "company_name": os.environ.get("COMPANY_NAME", "Eco Recicle"),
        "today_iso": date.today().isoformat(),
    }


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = get_db().execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            return redirect(url_for("dashboard"))
        flash("Usuário ou senha inválidos.", "error")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@login_required
def dashboard():
    db = get_db()
    today = date.today().isoformat()
    month_prefix = today[:7]

    today_summary = db.execute(
        """
        SELECT COALESCE(SUM(total_kg),0) AS kg, COALESCE(SUM(total_amount),0) AS valor, COUNT(*) AS compras
        FROM purchases WHERE purchase_date = ?
        """,
        (today,),
    ).fetchone()
    today_sales_summary = db.execute(
        """
        SELECT COALESCE(SUM(total_kg),0) AS kg, COALESCE(SUM(total_amount),0) AS valor, COUNT(*) AS vendas
        FROM sales WHERE sale_date = ?
        """,
        (today,),
    ).fetchone()
    month_summary = db.execute(
        """
        SELECT COALESCE(SUM(total_kg),0) AS kg, COALESCE(SUM(total_amount),0) AS valor, COUNT(*) AS compras
        FROM purchases WHERE substr(purchase_date,1,7) = ?
        """,
        (month_prefix,),
    ).fetchone()
    month_sales_summary = db.execute(
        """
        SELECT COALESCE(SUM(total_kg),0) AS kg, COALESCE(SUM(total_amount),0) AS valor, COUNT(*) AS vendas
        FROM sales WHERE substr(sale_date,1,7) = ?
        """,
        (month_prefix,),
    ).fetchone()
    material_totals = db.execute(
        """
        SELECT material_name_snapshot AS material, COALESCE(SUM(weight_kg),0) AS kg, COALESCE(SUM(subtotal),0) AS valor
        FROM purchase_items pi
        JOIN purchases p ON p.id = pi.purchase_id
        WHERE substr(p.purchase_date,1,7) = ?
        GROUP BY material_name_snapshot
        ORDER BY valor DESC
        LIMIT 8
        """,
        (month_prefix,),
    ).fetchall()
    sales_material_totals = db.execute(
        """
        SELECT material_name_snapshot AS material, COALESCE(SUM(weight_kg),0) AS kg, COALESCE(SUM(subtotal),0) AS valor
        FROM sale_items si
        JOIN sales s ON s.id = si.sale_id
        WHERE substr(s.sale_date,1,7) = ?
        GROUP BY material_name_snapshot
        ORDER BY valor DESC
        LIMIT 8
        """,
        (month_prefix,),
    ).fetchall()
    last_purchases = db.execute(
        """
        SELECT * FROM purchases ORDER BY purchase_date DESC, id DESC LIMIT 8
        """
    ).fetchall()
    last_sales = db.execute(
        """
        SELECT * FROM sales ORDER BY sale_date DESC, id DESC LIMIT 8
        """
    ).fetchall()
    stock_rows = get_stock_rows(db, limit=8)
    all_stock_rows = get_stock_rows(db)
    stock_summary = stock_totals(all_stock_rows)
    return render_template(
        "dashboard.html",
        today_summary=today_summary,
        today_sales_summary=today_sales_summary,
        month_summary=month_summary,
        month_sales_summary=month_sales_summary,
        month_result=(month_sales_summary["valor"] or 0) - (month_summary["valor"] or 0),
        material_totals=material_totals,
        sales_material_totals=sales_material_totals,
        last_purchases=last_purchases,
        last_sales=last_sales,
        stock_rows=stock_rows,
        stock_summary=stock_summary,
    )


@app.route("/compras")
@login_required
def purchases():
    db = get_db()
    q = request.args.get("q", "").strip()
    start = request.args.get("inicio", "").strip()
    end = request.args.get("fim", "").strip()

    clauses = []
    params: List[Any] = []
    if q:
        clauses.append("(p.person_name_snapshot LIKE ? OR p.notes LIKE ? OR EXISTS (SELECT 1 FROM purchase_items pi WHERE pi.purchase_id = p.id AND pi.material_name_snapshot LIKE ?))")
        params.extend([f"%{q}%", f"%{q}%", f"%{q}%"])
    if start:
        clauses.append("p.purchase_date >= ?")
        params.append(start)
    if end:
        clauses.append("p.purchase_date <= ?")
        params.append(end)
    where = "WHERE " + " AND ".join(clauses) if clauses else ""

    rows = db.execute(
        f"""
        SELECT p.*, (
            SELECT GROUP_CONCAT(material_name_snapshot || ' (' || printf('%.3f', weight_kg) || 'kg)', ', ')
            FROM purchase_items pi WHERE pi.purchase_id = p.id
        ) AS materiais
        FROM purchases p
        {where}
        ORDER BY p.purchase_date DESC, p.id DESC
        LIMIT 300
        """,
        params,
    ).fetchall()
    totals = db.execute(
        f"SELECT COALESCE(SUM(total_kg),0) AS kg, COALESCE(SUM(total_amount),0) AS valor, COUNT(*) AS compras FROM purchases p {where}",
        params,
    ).fetchone()
    return render_template("purchases.html", rows=rows, totals=totals, q=q, start=start, end=end)


@app.route("/compras/nova", methods=["GET", "POST"])
@login_required
def new_purchase():
    db = get_db()
    if request.method == "POST":
        purchase_date = request.form.get("purchase_date") or date.today().isoformat()
        person_name = request.form.get("person_name", "").strip() or "Fornecedor sem nome"
        phone = request.form.get("phone", "").strip()
        notes = request.form.get("notes", "").strip()
        payment_method = request.form.get("payment_method", "Pix").strip() or "Não informado"

        person = db.execute("SELECT * FROM people WHERE lower(name) = lower(?) LIMIT 1", (person_name,)).fetchone()
        if person:
            person_id = person["id"]
            if phone and phone != (person["phone"] or ""):
                db.execute("UPDATE people SET phone = ? WHERE id = ?", (phone, person_id))
        else:
            cur = db.execute(
                "INSERT INTO people (name, phone, kind, created_at) VALUES (?, ?, 'fornecedor', ?)",
                (person_name, phone, datetime.now().isoformat(timespec="seconds")),
            )
            person_id = cur.lastrowid

        material_ids = request.form.getlist("material_id[]")
        weights = request.form.getlist("weight_kg[]")
        prices = request.form.getlist("price_per_kg[]")

        items = []
        total_kg = 0.0
        total_amount = 0.0
        for mat_id, weight_raw, price_raw in zip(material_ids, weights, prices):
            try:
                weight = float((weight_raw or "0").replace(",", "."))
                price = float((price_raw or "0").replace(",", "."))
            except ValueError:
                continue
            if not mat_id or weight <= 0:
                continue
            mat = db.execute("SELECT * FROM materials WHERE id = ?", (mat_id,)).fetchone()
            if not mat:
                continue
            subtotal = round(weight * price, 2)
            total_kg += weight
            total_amount += subtotal
            items.append((mat["id"], mat["name"], weight, price, subtotal))

        if not items:
            flash("Adicione pelo menos um material com peso maior que zero.", "error")
            return redirect(url_for("new_purchase"))

        cur = db.execute(
            """
            INSERT INTO purchases (person_id, person_name_snapshot, purchase_date, notes, payment_method, total_kg, total_amount, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                person_id,
                person_name,
                purchase_date,
                notes,
                payment_method,
                round(total_kg, 3),
                round(total_amount, 2),
                datetime.now().isoformat(timespec="seconds"),
            ),
        )
        purchase_id = cur.lastrowid
        db.executemany(
            """
            INSERT INTO purchase_items (purchase_id, material_id, material_name_snapshot, weight_kg, price_per_kg, subtotal)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [(purchase_id, mat_id, name, weight, price, subtotal) for mat_id, name, weight, price, subtotal in items],
        )
        db.commit()
        flash("Compra registrada com sucesso.", "success")
        return redirect(url_for("receipt", purchase_id=purchase_id))

    materials = db.execute("SELECT * FROM materials WHERE active = 1 ORDER BY name").fetchall()
    people = db.execute("SELECT * FROM people ORDER BY name LIMIT 500").fetchall()
    return render_template("new_purchase.html", materials=materials, people=people)


@app.route("/compras/<int:purchase_id>/recibo")
@login_required
def receipt(purchase_id: int):
    db = get_db()
    purchase = db.execute("SELECT * FROM purchases WHERE id = ?", (purchase_id,)).fetchone()
    if not purchase:
        flash("Compra não encontrada.", "error")
        return redirect(url_for("purchases"))
    person = None
    if purchase["person_id"]:
        person = db.execute("SELECT * FROM people WHERE id = ?", (purchase["person_id"],)).fetchone()
    items = db.execute("SELECT * FROM purchase_items WHERE purchase_id = ? ORDER BY id", (purchase_id,)).fetchall()
    return render_template("receipt.html", purchase=purchase, person=person, items=items)


@app.route("/compras/<int:purchase_id>/recibo/pdf")
@login_required
def receipt_pdf(purchase_id: int):
    db = get_db()
    purchase = db.execute("SELECT * FROM purchases WHERE id = ?", (purchase_id,)).fetchone()
    if not purchase:
        flash("Compra não encontrada.", "error")
        return redirect(url_for("purchases"))
    person = None
    if purchase["person_id"]:
        person = db.execute("SELECT * FROM people WHERE id = ?", (purchase["person_id"],)).fetchone()
    items = db.execute("SELECT * FROM purchase_items WHERE purchase_id = ? ORDER BY id", (purchase_id,)).fetchall()
    meta = [
        ("Recibo", f"{purchase['id']:05d}"),
        ("Data", br_date(purchase["purchase_date"])),
        ("Pagamento", purchase["payment_method"] or "Nao informado"),
        ("Fornecedor", purchase["person_name_snapshot"]),
    ]
    if person and person["phone"]:
        meta.append(("Telefone", person["phone"]))
    if person and person["doc"]:
        meta.append(("Documento", person["doc"]))
    item_rows = [(item["material_name_snapshot"], f"{kg(item['weight_kg'])} kg x {money(item['price_per_kg'])}/kg", money(item["subtotal"])) for item in items]
    totals = [("Peso total", f"{kg(purchase['total_kg'])} kg"), ("Total pago", money(purchase["total_amount"]))]
    filename = f"recibo-eco-recicle-{purchase_id:05d}.pdf"
    return _thermal_pdf_response("Recibo de compra", meta, item_rows, totals, purchase["notes"], filename)


@app.post("/compras/<int:purchase_id>/excluir")
@login_required
def delete_purchase(purchase_id: int):
    db = get_db()
    db.execute("DELETE FROM purchase_items WHERE purchase_id = ?", (purchase_id,))
    db.execute("DELETE FROM purchases WHERE id = ?", (purchase_id,))
    db.commit()
    flash("Compra excluída.", "success")
    return redirect(url_for("purchases"))


@app.route("/vendas")
@login_required
def sales():
    db = get_db()
    q = request.args.get("q", "").strip()
    start = request.args.get("inicio", "").strip()
    end = request.args.get("fim", "").strip()

    clauses = []
    params: List[Any] = []
    if q:
        clauses.append("(s.buyer_name_snapshot LIKE ? OR s.notes LIKE ? OR EXISTS (SELECT 1 FROM sale_items si WHERE si.sale_id = s.id AND si.material_name_snapshot LIKE ?))")
        params.extend([f"%{q}%", f"%{q}%", f"%{q}%"])
    if start:
        clauses.append("s.sale_date >= ?")
        params.append(start)
    if end:
        clauses.append("s.sale_date <= ?")
        params.append(end)
    where = "WHERE " + " AND ".join(clauses) if clauses else ""

    rows = db.execute(
        f"""
        SELECT s.*, (
            SELECT GROUP_CONCAT(material_name_snapshot || ' (' || printf('%.3f', weight_kg) || 'kg)', ', ')
            FROM sale_items si WHERE si.sale_id = s.id
        ) AS materiais
        FROM sales s
        {where}
        ORDER BY s.sale_date DESC, s.id DESC
        LIMIT 300
        """,
        params,
    ).fetchall()
    totals = db.execute(
        f"SELECT COALESCE(SUM(total_kg),0) AS kg, COALESCE(SUM(total_amount),0) AS valor, COUNT(*) AS vendas FROM sales s {where}",
        params,
    ).fetchone()
    return render_template("sales.html", rows=rows, totals=totals, q=q, start=start, end=end)


@app.route("/vendas/nova", methods=["GET", "POST"])
@login_required
def new_sale():
    db = get_db()
    if request.method == "POST":
        sale_date = request.form.get("sale_date") or date.today().isoformat()
        buyer_name = request.form.get("buyer_name", "").strip() or "Comprador sem nome"
        phone = request.form.get("phone", "").strip()
        notes = request.form.get("notes", "").strip()
        payment_method = request.form.get("payment_method", "Pix").strip() or "Não informado"

        person = db.execute("SELECT * FROM people WHERE lower(name) = lower(?) LIMIT 1", (buyer_name,)).fetchone()
        if person:
            person_id = person["id"]
            if phone and phone != (person["phone"] or ""):
                db.execute("UPDATE people SET phone = ? WHERE id = ?", (phone, person_id))
        else:
            cur = db.execute(
                "INSERT INTO people (name, phone, kind, created_at) VALUES (?, ?, 'comprador', ?)",
                (buyer_name, phone, datetime.now().isoformat(timespec="seconds")),
            )
            person_id = cur.lastrowid

        material_ids = request.form.getlist("material_id[]")
        weights = request.form.getlist("weight_kg[]")
        prices = request.form.getlist("price_per_kg[]")

        items = []
        total_kg = 0.0
        total_amount = 0.0
        for mat_id, weight_raw, price_raw in zip(material_ids, weights, prices):
            try:
                weight = float((weight_raw or "0").replace(",", "."))
                price = float((price_raw or "0").replace(",", "."))
            except ValueError:
                continue
            if not mat_id or weight <= 0:
                continue
            mat = db.execute("SELECT * FROM materials WHERE id = ?", (mat_id,)).fetchone()
            if not mat:
                continue
            subtotal = round(weight * price, 2)
            total_kg += weight
            total_amount += subtotal
            items.append((mat["id"], mat["name"], weight, price, subtotal))

        if not items:
            flash("Adicione pelo menos um material com peso maior que zero.", "error")
            return redirect(url_for("new_sale"))

        cur = db.execute(
            """
            INSERT INTO sales (person_id, buyer_name_snapshot, sale_date, notes, payment_method, total_kg, total_amount, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                person_id,
                buyer_name,
                sale_date,
                notes,
                payment_method,
                round(total_kg, 3),
                round(total_amount, 2),
                datetime.now().isoformat(timespec="seconds"),
            ),
        )
        sale_id = cur.lastrowid
        db.executemany(
            """
            INSERT INTO sale_items (sale_id, material_id, material_name_snapshot, weight_kg, price_per_kg, subtotal)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [(sale_id, mat_id, name, weight, price, subtotal) for mat_id, name, weight, price, subtotal in items],
        )
        db.commit()
        flash("Venda/retirada registrada com sucesso.", "success")
        return redirect(url_for("sale_receipt", sale_id=sale_id))

    materials = db.execute("SELECT * FROM materials WHERE active = 1 ORDER BY name").fetchall()
    people = db.execute("SELECT * FROM people ORDER BY name LIMIT 500").fetchall()
    return render_template("new_sale.html", materials=materials, people=people)


@app.route("/vendas/<int:sale_id>/recibo")
@login_required
def sale_receipt(sale_id: int):
    db = get_db()
    sale = db.execute("SELECT * FROM sales WHERE id = ?", (sale_id,)).fetchone()
    if not sale:
        flash("Venda não encontrada.", "error")
        return redirect(url_for("sales"))
    person = None
    if sale["person_id"]:
        person = db.execute("SELECT * FROM people WHERE id = ?", (sale["person_id"],)).fetchone()
    items = db.execute("SELECT * FROM sale_items WHERE sale_id = ? ORDER BY id", (sale_id,)).fetchall()
    return render_template("sale_receipt.html", sale=sale, person=person, items=items)


@app.route("/vendas/<int:sale_id>/recibo/pdf")
@login_required
def sale_receipt_pdf(sale_id: int):
    db = get_db()
    sale = db.execute("SELECT * FROM sales WHERE id = ?", (sale_id,)).fetchone()
    if not sale:
        flash("Venda não encontrada.", "error")
        return redirect(url_for("sales"))
    person = None
    if sale["person_id"]:
        person = db.execute("SELECT * FROM people WHERE id = ?", (sale["person_id"],)).fetchone()
    items = db.execute("SELECT * FROM sale_items WHERE sale_id = ? ORDER BY id", (sale_id,)).fetchall()
    meta = [
        ("Numero", f"{sale['id']:05d}"),
        ("Data", br_date(sale["sale_date"])),
        ("Recebimento", sale["payment_method"] or "Nao informado"),
        ("Comprador", sale["buyer_name_snapshot"]),
    ]
    if person and person["phone"]:
        meta.append(("Telefone", person["phone"]))
    item_rows = [(item["material_name_snapshot"], f"{kg(item['weight_kg'])} kg x {money(item['price_per_kg'])}/kg", money(item["subtotal"])) for item in items]
    totals = [("Peso total", f"{kg(sale['total_kg'])} kg"), ("Total recebido", money(sale["total_amount"]))]
    filename = f"comprovante-eco-recicle-{sale_id:05d}.pdf"
    return _thermal_pdf_response("Comprovante de venda", meta, item_rows, totals, sale["notes"], filename)


@app.post("/vendas/<int:sale_id>/excluir")
@login_required
def delete_sale(sale_id: int):
    db = get_db()
    db.execute("DELETE FROM sale_items WHERE sale_id = ?", (sale_id,))
    db.execute("DELETE FROM sales WHERE id = ?", (sale_id,))
    db.commit()
    flash("Venda excluída.", "success")
    return redirect(url_for("sales"))


@app.route("/estoque")
@login_required
def stock():
    db = get_db()
    rows = get_stock_rows(db)
    totals = stock_totals(rows)
    return render_template("stock.html", rows=rows, totals=totals)


@app.route("/materiais", methods=["GET", "POST"])
@login_required
def materials():
    db = get_db()
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        price = request.form.get("price_per_kg", "0").replace(",", ".")
        sale_price = request.form.get("sale_price_per_kg", price).replace(",", ".")
        try:
            price_float = float(price)
        except ValueError:
            price_float = 0.0
        try:
            sale_price_float = float(sale_price)
        except ValueError:
            sale_price_float = price_float
        if name:
            db.execute(
                "INSERT INTO materials (name, price_per_kg, sale_price_per_kg, active, created_at) VALUES (?, ?, ?, 1, ?) ON CONFLICT(name) DO UPDATE SET price_per_kg = excluded.price_per_kg, sale_price_per_kg = excluded.sale_price_per_kg, active = 1",
                (name, price_float, sale_price_float, datetime.now().isoformat(timespec="seconds")),
            )
            db.commit()
            flash("Material salvo.", "success")
        return redirect(url_for("materials"))

    rows = db.execute("SELECT * FROM materials ORDER BY active DESC, name").fetchall()
    return render_template("materials.html", rows=rows)


@app.post("/materiais/<int:material_id>/editar")
@login_required
def edit_material(material_id: int):
    db = get_db()
    name = request.form.get("name", "").strip()
    price = request.form.get("price_per_kg", "0").replace(",", ".")
    sale_price = request.form.get("sale_price_per_kg", price).replace(",", ".")
    active = 1 if request.form.get("active") == "on" else 0
    try:
        price_float = float(price)
    except ValueError:
        price_float = 0.0
    try:
        sale_price_float = float(sale_price)
    except ValueError:
        sale_price_float = price_float
    if name:
        db.execute("UPDATE materials SET name = ?, price_per_kg = ?, sale_price_per_kg = ?, active = ? WHERE id = ?", (name, price_float, sale_price_float, active, material_id))
        db.commit()
        flash("Material atualizado.", "success")
    return redirect(url_for("materials"))


@app.route("/pessoas", methods=["GET", "POST"])
@login_required
def people():
    db = get_db()
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        doc = request.form.get("doc", "").strip()
        address = request.form.get("address", "").strip()
        if name:
            db.execute(
                "INSERT INTO people (name, phone, doc, address, kind, created_at) VALUES (?, ?, ?, ?, 'fornecedor', ?)",
                (name, phone, doc, address, datetime.now().isoformat(timespec="seconds")),
            )
            db.commit()
            flash("Pessoa salva.", "success")
        return redirect(url_for("people"))

    q = request.args.get("q", "").strip()
    params: List[Any] = []
    where = ""
    if q:
        where = "WHERE name LIKE ? OR phone LIKE ? OR doc LIKE ?"
        params = [f"%{q}%", f"%{q}%", f"%{q}%"]
    rows = db.execute(f"SELECT * FROM people {where} ORDER BY name LIMIT 500", params).fetchall()
    return render_template("people.html", rows=rows, q=q)


@app.post("/pessoas/<int:person_id>/editar")
@login_required
def edit_person(person_id: int):
    db = get_db()
    db.execute(
        "UPDATE people SET name = ?, phone = ?, doc = ?, address = ? WHERE id = ?",
        (
            request.form.get("name", "").strip(),
            request.form.get("phone", "").strip(),
            request.form.get("doc", "").strip(),
            request.form.get("address", "").strip(),
            person_id,
        ),
    )
    db.commit()
    flash("Pessoa atualizada.", "success")
    return redirect(url_for("people"))


@app.route("/relatorios")
@login_required
def reports():
    db = get_db()
    start = request.args.get("inicio", date.today().replace(day=1).isoformat())
    end = request.args.get("fim", date.today().isoformat())
    summary = db.execute(
        """
        SELECT COALESCE(SUM(total_kg),0) AS kg, COALESCE(SUM(total_amount),0) AS valor, COUNT(*) AS compras
        FROM purchases WHERE purchase_date BETWEEN ? AND ?
        """,
        (start, end),
    ).fetchone()
    sales_summary = db.execute(
        """
        SELECT COALESCE(SUM(total_kg),0) AS kg, COALESCE(SUM(total_amount),0) AS valor, COUNT(*) AS vendas
        FROM sales WHERE sale_date BETWEEN ? AND ?
        """,
        (start, end),
    ).fetchone()
    by_material = db.execute(
        """
        SELECT pi.material_name_snapshot AS material, COALESCE(SUM(pi.weight_kg),0) AS kg, COALESCE(SUM(pi.subtotal),0) AS valor
        FROM purchase_items pi
        JOIN purchases p ON p.id = pi.purchase_id
        WHERE p.purchase_date BETWEEN ? AND ?
        GROUP BY pi.material_name_snapshot
        ORDER BY valor DESC
        """,
        (start, end),
    ).fetchall()
    by_sale_material = db.execute(
        """
        SELECT si.material_name_snapshot AS material, COALESCE(SUM(si.weight_kg),0) AS kg, COALESCE(SUM(si.subtotal),0) AS valor
        FROM sale_items si
        JOIN sales s ON s.id = si.sale_id
        WHERE s.sale_date BETWEEN ? AND ?
        GROUP BY si.material_name_snapshot
        ORDER BY valor DESC
        """,
        (start, end),
    ).fetchall()
    by_person = db.execute(
        """
        SELECT person_name_snapshot AS pessoa, COALESCE(SUM(total_kg),0) AS kg, COALESCE(SUM(total_amount),0) AS valor, COUNT(*) AS compras
        FROM purchases
        WHERE purchase_date BETWEEN ? AND ?
        GROUP BY person_name_snapshot
        ORDER BY valor DESC
        LIMIT 20
        """,
        (start, end),
    ).fetchall()
    by_buyer = db.execute(
        """
        SELECT buyer_name_snapshot AS pessoa, COALESCE(SUM(total_kg),0) AS kg, COALESCE(SUM(total_amount),0) AS valor, COUNT(*) AS vendas
        FROM sales
        WHERE sale_date BETWEEN ? AND ?
        GROUP BY buyer_name_snapshot
        ORDER BY valor DESC
        LIMIT 20
        """,
        (start, end),
    ).fetchall()
    stock_rows = get_stock_rows(db)
    stock_summary = stock_totals(stock_rows)
    return render_template(
        "reports.html",
        start=start,
        end=end,
        summary=summary,
        sales_summary=sales_summary,
        result=(sales_summary["valor"] or 0) - (summary["valor"] or 0),
        by_material=by_material,
        by_sale_material=by_sale_material,
        by_person=by_person,
        by_buyer=by_buyer,
        stock_rows=stock_rows,
        stock_summary=stock_summary,
    )


@app.route("/exportar/compras.csv")
@login_required
def export_csv():
    db = get_db()
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow(["ID", "Data", "Fornecedor", "Material", "Kg", "Preco por kg", "Subtotal", "Forma pagamento", "Observacao"])
    rows = db.execute(
        """
        SELECT p.id, p.purchase_date, p.person_name_snapshot, pi.material_name_snapshot, pi.weight_kg, pi.price_per_kg, pi.subtotal, p.payment_method, p.notes
        FROM purchases p
        JOIN purchase_items pi ON pi.purchase_id = p.id
        ORDER BY p.purchase_date DESC, p.id DESC
        """
    ).fetchall()
    for r in rows:
        writer.writerow([r["id"], br_date(r["purchase_date"]), r["person_name_snapshot"], r["material_name_snapshot"], kg(r["weight_kg"]), money(r["price_per_kg"]), money(r["subtotal"]), r["payment_method"] or "", r["notes"] or ""])
    data = output.getvalue().encode("utf-8-sig")
    return Response(
        data,
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=compras_eco_recicle.csv"},
    )


@app.route("/exportar/vendas.csv")
@login_required
def export_sales_csv():
    db = get_db()
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow(["ID", "Data", "Comprador", "Material", "Kg", "Preco por kg", "Subtotal", "Forma recebimento", "Observacao"])
    rows = db.execute(
        """
        SELECT s.id, s.sale_date, s.buyer_name_snapshot, si.material_name_snapshot, si.weight_kg, si.price_per_kg, si.subtotal, s.payment_method, s.notes
        FROM sales s
        JOIN sale_items si ON si.sale_id = s.id
        ORDER BY s.sale_date DESC, s.id DESC
        """
    ).fetchall()
    for r in rows:
        writer.writerow([r["id"], br_date(r["sale_date"]), r["buyer_name_snapshot"], r["material_name_snapshot"], kg(r["weight_kg"]), money(r["price_per_kg"]), money(r["subtotal"]), r["payment_method"] or "", r["notes"] or ""])
    data = output.getvalue().encode("utf-8-sig")
    return Response(
        data,
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=vendas_eco_recicle.csv"},
    )


@app.route("/saude")
def healthcheck():
    return {"status": "ok"}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=True)
