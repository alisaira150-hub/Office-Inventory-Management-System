
import os, sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse
from datetime import datetime
from html import escape

HERE=os.path.dirname(os.path.abspath(__file__))
DB=os.path.join(HERE,"office_inventory.db")
PORT=8000

def connect():
    c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c

def setup():
    c=connect()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS items(id INTEGER PRIMARY KEY, code TEXT UNIQUE NOT NULL, name TEXT NOT NULL, category TEXT NOT NULL, unit TEXT NOT NULL, min_stock INTEGER NOT NULL DEFAULT 0);
    CREATE TABLE IF NOT EXISTS movements(id INTEGER PRIMARY KEY, item_id INTEGER NOT NULL, kind TEXT NOT NULL, qty INTEGER NOT NULL, note TEXT, created TEXT NOT NULL, FOREIGN KEY(item_id) REFERENCES items(id));
    """)
    if c.execute("SELECT COUNT(*) FROM items").fetchone()[0]==0:
        samples=[("ST-001","A4 Paper","Stationery","Ream",5,20),("ST-002","Blue Ball Pen","Stationery","Piece",15,50),("ST-003","Office File","Office Supplies","Piece",10,30),("IT-001","Printer Cartridge","IT Supplies","Piece",3,8),("EL-001","Extension Board","Electrical","Piece",4,12),("ST-004","Sticky Notes","Stationery","Pack",5,18)]
        for code,name,cat,unit,minimum,qty in samples:
            cur=c.execute("INSERT INTO items(code,name,category,unit,min_stock) VALUES(?,?,?,?,?)",(code,name,cat,unit,minimum))
            c.execute("INSERT INTO movements(item_id,kind,qty,note,created) VALUES(?,?,?,?,?)",(cur.lastrowid,"INWARD",qty,"Opening balance","2026-11-01 09:00"))
        c.execute("INSERT INTO movements(item_id,kind,qty,note,created) VALUES(1,'ISSUE',6,'Department use','2026-11-01 10:15')")
        c.execute("INSERT INTO movements(item_id,kind,qty,note,created) VALUES(2,'ISSUE',38,'Office use','2026-11-01 10:30')")
    c.commit(); c.close()

def inventory(c, search=""):
    return c.execute("""
      SELECT i.id,i.code,i.name,i.category,i.unit,i.min_stock,
      COALESCE(SUM(CASE WHEN m.kind='INWARD' THEN m.qty ELSE -m.qty END),0) AS stock
      FROM items i LEFT JOIN movements m ON m.item_id=i.id
      WHERE (?='' OR i.code LIKE ? OR i.name LIKE ? OR i.category LIKE ?)
      GROUP BY i.id ORDER BY i.name
    """,(search,"%"+search+"%","%"+search+"%","%"+search+"%")).fetchall()

def render(search="", notice="", error=""):
    c=connect(); all_items=inventory(c); items=inventory(c,search)
    recent=c.execute("""SELECT m.*,i.name,i.code FROM movements m JOIN items i ON i.id=m.item_id ORDER BY m.id DESC LIMIT 7""").fetchall()
    total_units=sum(x["stock"] for x in all_items)
    low=sum(x["stock"]<=x["min_stock"] for x in all_items)
    esc=escape
    item_rows="".join(
      '<tr><td><b>'+esc(x["code"])+'</b></td><td><b>'+esc(x["name"])+'</b><small>'+esc(x["category"])+'</small></td><td>'+esc(x["unit"])+'</td><td><b>'+str(x["stock"])+'</b></td><td>'+str(x["min_stock"])+'</td><td><span class="tag '+("low" if x["stock"]<=x["min_stock"] else "ok")+'">'+("Low stock" if x["stock"]<=x["min_stock"] else "In stock")+'</span></td></tr>'
      for x in items) or '<tr><td colspan="6" class="empty">No matching items</td></tr>'
    tx_rows="".join(
      '<tr><td class="'+("green" if x["kind"]=="INWARD" else "orange")+'">'+("＋ Inward" if x["kind"]=="INWARD" else "− Issue")+'</td><td>'+esc(x["name"])+'</td><td><b>'+str(x["qty"])+'</b></td><td>'+esc(x["note"] or "—")+'</td><td>'+esc(x["created"])+'</td></tr>'
      for x in recent) or '<tr><td colspan="5" class="empty">No transactions</td></tr>'
    opts="".join('<option value="'+str(x["id"])+'">'+esc(x["code"])+' — '+esc(x["name"])+' (Available: '+str(x["stock"])+')</option>' for x in all_items)
    c.close()
    message=('<div class="notice">'+esc(notice)+'</div>' if notice else '')+('<div class="error">'+esc(error)+'</div>' if error else '')
    html_doc = """<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>OfficeStock | Inventory Dashboard</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#f4f6fb;color:#202b3c;font-family:Segoe UI,Arial,sans-serif}.layout{display:flex;min-height:100vh}aside{width:225px;background:#14213d;color:#fff;padding:28px 18px;flex-shrink:0}.brand{font-size:19px;font-weight:750;margin:0 8px 45px;display:flex;gap:12px;align-items:center}.logo{background:#4777ef;border-radius:11px;padding:10px}.navtitle{font-size:10px;color:#8f9bb3;letter-spacing:1.5px;margin:25px 10px 12px}nav a{display:block;color:#c3cde0;text-decoration:none;padding:12px;border-radius:8px;font-size:13px}nav a:first-child,nav a:hover{background:#293c62;color:#fff}.sidefoot{position:absolute;bottom:25px;font-size:11px;color:#a8b4c9;line-height:1.6}main{padding:30px 36px;max-width:1500px;margin:auto;flex:1}.top{display:flex;justify-content:space-between;margin-bottom:26px}.crumb,.muted{color:#8792a5;font-size:12px}h1{font-size:27px;margin:8px 0 4px}.user{font-size:12px;color:#526078}.avatar{display:inline-grid;place-items:center;background:#e4ebff;color:#315bc5;border-radius:50%;width:36px;height:36px;margin-right:8px;font-weight:bold}.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:15px;margin-bottom:20px}.card,.panel{background:white;border:1px solid #e8ecf3;border-radius:12px;box-shadow:0 3px 12px #24385b08}.card{padding:18px 20px}.cardhead{display:flex;justify-content:space-between;color:#7b8799;font-size:12px}.metric{font-size:29px;font-weight:750;margin-top:12px}.hint{font-size:11px;color:#9aa3b2;margin-top:4px}.ico{background:#edf2ff;color:#3569e8;padding:9px;border-radius:9px}.orangebg{background:#fff2e6;color:#d17b2c}.greenbg{background:#e9f8f0;color:#21945c}.redbg{background:#fff0f0;color:#d84e4e}.grid{display:grid;grid-template-columns:1.4fr 1fr;gap:17px;margin-bottom:19px}.head{padding:17px 19px;border-bottom:1px solid #edf0f5;display:flex;justify-content:space-between;align-items:center}h2{font-size:15px;margin:0}.body{padding:15px 18px;overflow:auto}table{width:100%;border-collapse:collapse;font-size:12px;white-space:nowrap}th{text-align:left;color:#8b95a6;font-size:10px;padding:10px;border-bottom:1px solid #edf0f5;text-transform:uppercase}td{padding:12px 10px;border-bottom:1px solid #f1f3f7;color:#4b586d}td small{display:block;color:#9aa3b2;margin-top:3px;font-size:10px}.tag{border-radius:20px;padding:5px 8px;font-size:10px;font-weight:650}.low{background:#fff1e8;color:#c77b32}.ok{background:#eaf8f0;color:#238c58}.green{color:#21945c;font-weight:bold}.orange{color:#d36b45;font-weight:bold}.empty{text-align:center;color:#9aa3b2;padding:20px}.search{display:flex;gap:7px}input,select{border:1px solid #dfe5ef;border-radius:7px;padding:9px 10px;font-size:12px;min-width:0}.search input{width:175px}button{border:0;border-radius:7px;background:#3569e8;color:white;padding:9px 13px;font-size:12px;font-weight:bold;cursor:pointer}.forms{display:grid;grid-template-columns:repeat(3,1fr);gap:17px}.form{padding:18px}h3{font-size:14px;margin:0 0 14px}label{display:block;font-size:10px;color:#7b8799;font-weight:650;margin:9px 0}label input,label select{display:block;width:100%;margin-top:5px}.form button{width:100%;margin-top:8px}.notice,.error{padding:10px 14px;border-radius:8px;font-size:12px;margin-bottom:14px;background:#eaf8f0;color:#207c50}.error{background:#fff0f0;color:#b83c3c}.foot{text-align:right;color:#9aa3b2;font-size:10px;margin-top:20px}@media(max-width:1000px){.cards{grid-template-columns:repeat(2,1fr)}.forms{grid-template-columns:1fr 1fr}}@media(max-width:700px){aside{display:none}main{padding:18px}.grid,.forms{grid-template-columns:1fr}.cards{grid-template-columns:repeat(2,1fr)}.user{display:none}}
</style></head><body><div class="layout"><aside><div class="brand"><span class="logo">▦</span> Office<span style="color:#91b2ff">Stock</span></div><div class="navtitle">WORKSPACE</div><nav><a href="/">▦ &nbsp; Dashboard</a><a href="#inventory">▤ &nbsp; Inventory</a><a href="#transactions">↔ &nbsp; Stock Transactions</a></nav><div class="navtitle">MANAGEMENT</div><nav><a href="#add">＋ &nbsp; Add New Item</a><a href="#inward">↓ &nbsp; Stock Inward</a><a href="#issue">↑ &nbsp; Stock Issue</a></nav><div class="sidefoot">OFFICE INVENTORY SYSTEM<br>Local application · v1.0</div></aside><main>
<div class="top"><div><div class="crumb">Workspace / Dashboard</div><h1>Inventory Dashboard</h1><div class="muted">Monitor office supplies and stock movements in one place.</div></div><div class="user"><span class="avatar">IA</span><b>Inventory Admin</b><br><span style="margin-left:47px;color:#9aa3b2">Administrator</span></div></div>__MESSAGE__
<div class="cards"><div class="card"><div class="cardhead">Total Item Types <span class="ico">▤</span></div><div class="metric">__ITEMS__</div><div class="hint">Unique items registered</div></div><div class="card"><div class="cardhead">Available Units <span class="ico greenbg">▣</span></div><div class="metric">__UNITS__</div><div class="hint">Total current stock quantity</div></div><div class="card"><div class="cardhead">Low Stock Items <span class="ico orangebg">⚑</span></div><div class="metric">__LOW__</div><div class="hint">At or below minimum level</div></div><div class="card"><div class="cardhead">Recent Movements <span class="ico redbg">↔</span></div><div class="metric">__RECENT__</div><div class="hint">Latest recorded transactions</div></div></div>
<div class="grid"><section class="panel" id="inventory"><div class="head"><h2>Current Inventory</h2><form class="search"><input name="q" placeholder="Search item or code..." value="__SEARCH__"><button>Search</button></form></div><div class="body"><table><thead><tr><th>Item Code</th><th>Item Details</th><th>Unit</th><th>Available</th><th>Min.</th><th>Status</th></tr></thead><tbody>__ROWS__</tbody></table></div></section><section class="panel" id="transactions"><div class="head"><h2>Recent Transactions</h2><span class="muted">Latest activity</span></div><div class="body"><table><thead><tr><th>Type</th><th>Item</th><th>Qty</th><th>Note</th><th>Date</th></tr></thead><tbody>__TX__</tbody></table></div></section></div>
<div class="forms"><section class="panel form" id="add"><h3>＋ Add New Item</h3><form method="post" action="/add"><label>Item Code<input name="code" required placeholder="e.g. ST-005"></label><label>Item Name<input name="name" required></label><label>Category<input name="category" required></label><label>Unit<input name="unit" required placeholder="Piece / Pack / Ream"></label><label>Minimum Stock<input name="minimum" type="number" min="0" value="5" required></label><button>Add Item</button></form></section>
<section class="panel form" id="inward"><h3>↓ Stock Inward</h3><form method="post" action="/move"><input type="hidden" name="kind" value="INWARD"><label>Select Item<select name="item_id">__OPTIONS__</select></label><label>Received Quantity<input type="number" name="qty" min="1" required></label><label>Note<input name="note" placeholder="Supplier / reference"></label><button>Record Inward</button></form></section>
<section class="panel form" id="issue"><h3>↑ Stock Issue</h3><form method="post" action="/move"><input type="hidden" name="kind" value="ISSUE"><label>Select Item<select name="item_id">__OPTIONS__</select></label><label>Issue Quantity<input type="number" name="qty" min="1" required></label><label>Issued To / Note<input name="note" placeholder="Department / recipient"></label><button>Record Issue</button></form></section></div><div class="foot">Office Inventory Management System · Python + SQLite · Local database</div></main></div></body></html>"""
    html_doc = html_doc.replace("__MESSAGE__",message).replace("__ITEMS__",str(len(all_items))).replace("__UNITS__",str(total_units)).replace("__LOW__",str(low)).replace("__RECENT__",str(len(recent))).replace("__SEARCH__",esc(search)).replace("__ROWS__",item_rows).replace("__TX__",tx_rows).replace("__OPTIONS__",opts)
    return html_doc

class Handler(BaseHTTPRequestHandler):
    def respond(self,content):
        b=content.encode(); self.send_response(200); self.send_header("Content-Type","text/html; charset=utf-8"); self.send_header("Content-Length",str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        q=parse_qs(urlparse(self.path).query).get("q",[""])[0]; self.respond(render(q))
    def do_POST(self):
        data={k:v[0] for k,v in parse_qs(self.rfile.read(int(self.headers.get("Content-Length",0))).decode()).items()}
        c=connect(); notice=""; error=""
        try:
            if self.path=="/add":
                c.execute("INSERT INTO items(code,name,category,unit,min_stock) VALUES(?,?,?,?,?)",(data["code"].strip().upper(),data["name"].strip(),data["category"].strip(),data["unit"].strip(),int(data["minimum"])))
                notice="Item added successfully."
            else:
                item=int(data["item_id"]); qty=int(data["qty"]); kind=data["kind"]
                stock=c.execute("SELECT COALESCE(SUM(CASE WHEN kind='INWARD' THEN qty ELSE -qty END),0) FROM movements WHERE item_id=?",(item,)).fetchone()[0]
                if qty<1: raise ValueError("Quantity must be greater than zero.")
                if kind=="ISSUE" and qty>stock: raise ValueError("Insufficient stock. Available quantity is "+str(stock)+".")
                c.execute("INSERT INTO movements(item_id,kind,qty,note,created) VALUES(?,?,?,?,?)",(item,kind,qty,data.get("note",""),datetime.now().strftime("%Y-%m-%d %H:%M")))
                notice="Stock transaction recorded successfully."
            c.commit()
        except sqlite3.IntegrityError:
            c.rollback(); error="Item code already exists. Please use a unique code."
        except Exception as ex:
            c.rollback(); error=str(ex)
        finally: c.close()
        self.respond(render(notice=notice,error=error))
    def log_message(self,*args): pass

if __name__=="__main__":
    setup(); print("Office Inventory Dashboard: http://localhost:8000"); print("Press Ctrl+C to stop.")
    ThreadingHTTPServer(("127.0.0.1",PORT),Handler).serve_forever()
