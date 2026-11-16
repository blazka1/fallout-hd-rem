"""Mark this validated v3 base as connected without changing any image bytes."""
import json
from pathlib import Path

root = Path(__file__).resolve().parents[3]
def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))
def write(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

report = read(root / "build/hd-world-pilot/integration-manifest.json")
assert report["world_checks"]["passed"] == 107 and report["world_checks"]["failed"] == 0
assert report["menu_checks"] == {"passed": 139, "failed": 0}
assert report["fallback_checks"]["passed"] == 56 and report["fallback_checks"]["failed"] == 0
path = root / "work/hd-world-pilot/README.txt"
text = path.read_text(encoding="utf-8-sig")
text = text.replace("СТАТУС ПРОВЕРОК V3: ОЖИДАЕТСЯ ФИНАЛЬНЫЙ ПРОГОН", "СТАТУС V3: ПОДКЛЮЧЕНО И ПРОВЕРЕНО В CE")
text = text.replace("Ожидаемый набор: 107 проверок мира, 139 меню, 56 резервной загрузки.\nЭти числа до финального прогона не являются результатом PASS для v3.",
                    "Финальный v3: мир 107 PASS, меню 139 PASS, резервная загрузка 56 PASS.\nВсего 302 проверки, 0 ошибок. Все отчёты относятся к одному EXE.")
text = text.replace("Предыдущий полный прогон v2 дал 107 PASS, 0 FAIL. В нём загружены все", "Финальный прогон v3 дал 107 PASS, 0 FAIL. В нём загружены все")
path.write_text(text, encoding="utf-8")
path = root / "work/hd-world-pilot/task.json"
data = read(path)
data["status"] = "Static base integrated and verified in isolated CE runtime: 159 resources; 302 integration checks passed"
write(path, data)
path = root / "assets/hd/v13ent/v3-hybrid-base-x4/manifest.json"
data = read(path)
data.update(status="integrated_and_verified_in_isolated_ce", integrated_in_ce=True,
            integration_report="build/hd-world-pilot/integration-manifest.json",
            runtime="runtime/hd-world-pilot", executable_sha256=report["executable_sha256"])
write(path, data)
write(path.parent / "integration.json", {
    "status": data["status"], "world_checks": report["world_checks"],
    "menu_checks": report["menu_checks"], "fallback_checks": report["fallback_checks"],
    "executable_sha256": report["executable_sha256"], "report": data["integration_report"],
})
print("Recorded verified v3 integration; all PNG pixels unchanged.")
