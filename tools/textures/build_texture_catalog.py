"""Generate offline galleries and an editable-texture checklist from the inventory."""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
from ua import paths  # noqa: E402
CATALOG = paths.BUILD / "texture-catalog"

TEMPLATE = """<!doctype html><html lang="uk"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>__TITLE__</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#15191f;color:#edf0f4;font:16px system-ui,sans-serif}
header{padding:28px 4vw;background:#202731}h1{margin:0 0 12px;font-size:28px}a{color:#a7d9ff}
.controls{display:flex;gap:12px;flex-wrap:wrap;margin:18px 0}input,select,button{font:inherit;padding:9px 12px;border:1px solid #536072;border-radius:6px;background:#141a23;color:white}
input{flex:1;min-width:250px}main{padding:24px 4vw;display:grid;grid-template-columns:repeat(auto-fill,minmax(310px,1fr));gap:20px}
article{background:#222b37;border:1px solid #3c4a5d;border-radius:10px;overflow:hidden}article img{width:100%;height:250px;object-fit:contain;background:repeating-conic-gradient(#3d4249 0% 25%,#282d34 0% 50%) 0/24px 24px}
.body{padding:18px}.body h2{font-size:18px;margin:0 0 8px}.meta{font-size:13px;color:#bac5d6;overflow-wrap:anywhere}.note{line-height:1.45}.links{display:flex;gap:16px;flex-wrap:wrap}footer{padding:24px 4vw;display:flex;gap:12px;align-items:center}
</style><header><h1>__TITLE__</h1><div>__INTRO__</div><p><a href="index.html">Список для перекладу</a> · <a href="all-textures.html">Усі текстури</a> · <a href="TRANSLATION-LIST.md">Текстовий список</a></p>
<div class="controls"><input id="query" placeholder="Знайти за написом, назвою, ID або шляхом ресурсу"><select id="status"><option value="all">Усі категорії</option><option value="pending">Потрібно перекласти</option><option value="optional">Демоверсія — додатково</option><option value="review">Потрібен ручний розбір</option><option value="console">Консольні ресурси</option><option value="done">Уже готово у v0.1.1</option><option value="brand">Бренд або рейтинг</option></select></div><div id="summary"></div></header>
<main id="grid"></main><footer><button id="prev">Назад</button><span id="page"></span><button id="next">Далі</button></footer>
<script>
const rows=__DATA__;const pageSize=48;let page=0;
const statusNames={pending:'Потрібно перекласти',optional:'Демоверсія — додатково',review:'Потрібен ручний розбір',console:'Консольний ресурс',done:'Уже готово',brand:'Бренд або рейтинг',unreviewed:'Повний інвентар'};
const el=id=>document.getElementById(id);
function text(tag,value,cls){const node=document.createElement(tag);node.textContent=value;if(cls)node.className=cls;return node;}
function render(){const q=el('query').value.toLowerCase();const status=el('status').value;const found=rows.filter(r=>(status==='all'||r.status===status)&&JSON.stringify(r).toLowerCase().includes(q));const pages=Math.max(1,Math.ceil(found.length/pageSize));page=Math.min(page,pages-1);el('grid').replaceChildren();
for(const r of found.slice(page*pageSize,(page+1)*pageSize)){const card=document.createElement('article');const img=document.createElement('img');img.src=r.png;img.loading='lazy';img.alt=r.label;card.append(img);const body=document.createElement('div');body.className='body';body.append(text('h2',r.label));body.append(text('div',`${r.id} · ${r.width}×${r.height} · ${statusNames[r.status]}`,'meta'));body.append(text('p',r.note||r.ocr||'Напис автоматично не розпізнаний.','note'));for(const path of [...new Set(r.occurrences.map(o=>o.resource))])body.append(text('p',path,'meta'));const links=document.createElement('div');links.className='links';const link=document.createElement('a');link.href=r.png;link.download=r.png.split('/').pop();link.textContent='Відкрити / зберегти PNG';links.append(link);if(r.status!=='unreviewed'){const dds=document.createElement('a');dds.href=`to-translate/originals/${r.id}.dds`;dds.textContent='Оригінальний DDS';links.append(dds);}body.append(links);card.append(body);el('grid').append(card);}
el('summary').textContent=`Знайдено ${found.length} із ${rows.length}`;el('page').textContent=`Сторінка ${page+1} із ${pages}`;el('prev').disabled=page===0;el('next').disabled=page>=pages-1;}
el('query').oninput=()=>{page=0;render()};el('status').onchange=()=>{page=0;render()};el('prev').onclick=()=>{page--;render();window.scrollTo(0,0)};el('next').onclick=()=>{page++;render();window.scrollTo(0,0)};el('status').value='__DEFAULT__';render();
</script></html>"""


def gallery(name, title, intro, rows, default="all"):
    payload = json.dumps(rows, ensure_ascii=False).replace("<", "\\u003c")
    html = TEMPLATE.replace("__TITLE__", title).replace("__INTRO__", intro)
    html = html.replace("__DATA__", payload).replace("__DEFAULT__", default)
    (CATALOG / name).write_text(html, encoding="utf-8")


def main():
    inventory = json.loads((CATALOG / "inventory.json").read_text(encoding="utf-8"))
    selected = json.loads((CATALOG / "translation-list.json").read_text(encoding="utf-8"))
    ocr = {x["id"]: x.get("text", "") for x in json.loads((CATALOG / "ocr.json").read_text(encoding="utf-8-sig"))}
    gallery("index.html", "Текстури для перекладу", "Підготовлені PNG у початковому розмірі. Основні ресурси, додаткові матеріали й уже готові логотипи розділено за категоріями.", selected, "pending")
    raw = [{**item, "label": item["id"], "status": "unreviewed", "png": f"all/{item['id']}.png", "ocr": ocr.get(item["id"], "")} for item in inventory["textures"]]
    gallery("all-textures.html", "Повний інвентар текстур", f"{inventory['unique_textures']} унікальних текстур із чотирьох архівів. Тут також є матеріали без тексту; галерея дозволяє вручну перевірити дрібні написи, пропущені OCR.", raw)
    labels = {"pending": "Потрібно перекласти", "optional": "Демоверсія — додатково", "review": "Потрібен ручний розбір", "console": "Консольні ресурси", "done": "Уже готово у v0.1.1", "brand": "Бренд або рейтинг"}
    lines = ["# Текстури з написами — список для перекладу", "", "Підготовлено 3 жовтня 2026 року.", "",
             "[Галерея для перекладу](index.html) · [Повний інвентар](all-textures.html)", "",
             "Основний стартовий екран: [startup-english.png](../startup-screen/startup-english.png), 1024×1024. Зберегти переклад як `startup-english-ukrainian.png`.", "",
             "## Як редагувати", "",
             "PNG у `to-translate/` зберігають розмір, прозорість і положення елементів початкової текстури. Редагуйте лише написи. Зберігайте результат поруч із суфіксом `-ukrainian.png`; оригінальний PNG залишайте без змін. Для стартового екрана можна працювати з окремою папкою `graphics/startup-screen/`.", "",
             "Вивіски можуть займати лише частину атласу або бути повернутими. Не обрізайте полотно й не переставляйте інші елементи: гра використовує їхні координати. DDS з усіма mip-рівнями збережені в `to-translate/originals/`; `translation-list.json` містить SHA-256, офсети й усі місця використання.", "",
             "## Результат пошуку", "",
             f"Перевірено {inventory['scanned_resource_files']} GSC/DDS-файлів із GAME, RAIDERS, TEMPLE і CRUSADE; знайдено {inventory['dds_occurrences']} входжень DDS і {inventory['unique_textures']} унікальних текстур. Нерозібраних DDS після додаткового декодування немає. OCR виконано для 5936 текстур; три додаткові float-текстури переглянуті вручну й не містять написів. Для 77 кандидатів проведено збільшений OCR, для 174 витягнутих текстур — перевірку трьох поворотів (522 зображення). Написи в наведених основних ресурсах перевірено візуально.", "",
             "Інші мовні варіанти тих самих екранів збережені в повній галереї, але їх не потрібно перекладати окремо для нашої заміни англійської мови. Не всі ресурси архівів реально показуються у Steam PC-версії: демоекрани й консольні попередження позначені окремо. Відео BIK, шрифтові атласи FNT і текстові рядки TXT/CSV не входять до цього переліку зображень. Дрібні або стилізовані написи могли не розпізнатися, тому додано повний інвентар із PNG для додаткового огляду.", ""]
    for status, heading in labels.items():
        lines += [f"## {heading}", ""]
        for row in selected:
            if row["status"] != status:
                continue
            lines += [f"### {row['id']} — {row['label']}", "", f"[PNG для редагування]({row['png']}) · {row['width']}×{row['height']}", "", row["note"], "",
                      "Ресурси: " + "; ".join(f"`{x}`" for x in sorted({o['resource'] for o in row['occurrences']})), ""]
    (CATALOG / "TRANSLATION-LIST.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Built offline galleries and checklist: {len(selected)} selected resources, {len(raw)} total textures")


if __name__ == "__main__":
    main()
