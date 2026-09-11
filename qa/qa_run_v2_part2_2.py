        after_lines = open(LOG_FILE, encoding="utf-8", errors="ignore").read().splitlines() if os.path.exists(LOG_FILE) else []
        new_tb = sum(1 for l in after_lines[before:] if "Traceback" in l)
        try:
            fb = post("/feedback", {"token": TOKEN, "query": "qa", "think": "", "tool": "qa",
                                     "result": "qa", "ok": 1, "comment": "qa probe"})
            fb_ok = fb.get("ok") is True
        except Exception as e:
            fb_ok = False
            fb = str(e)
        try:
            st = json.loads(urllib.request.urlopen(BASE + "/status", timeout=10).read())
        except Exception as e:
            st = {"error": str(e)}
        print(f"{datetime.date.today()} {model_name_holder or 'unknown'}")
        print("\n=== SUMMARY ===")
        passed = sum(1 for r in results if r["verdict"] == "PASS")
        failed = sum(1 for r in results if r["verdict"] == "FAIL")
        print(f"PASS {passed} / FAIL {failed}")
        print(f"think: {think_count} из 17")
        print(f"Traceback in new log lines: {new_tb}")
        print(f"feedback ok: {fb_ok}")
        print(f"status: blocks={st.get('blocks')} tools={st.get('tools')}")
        print("\n=== FAIL DETAIL ===")
        for r in results:
            if r["verdict"] == "FAIL":
                print(f"  #{r['#']} {r.get('q','')[:40]} | ожидал {r.get('expected')} | получил {r.get('tools')} | {r.get('note')}")
        with open(r"D:\AI\tools\agent\qa\qa_results.json", "w", encoding="utf-8") as f:
            json.dump({"results": results,
                       "after": {"traceback_new": new_tb, "feedback_ok": fb_ok, "status": st}},
                      f, ensure_ascii=False, indent=2)
        print("\nsaved D:\\AI\\tools\\agent\\qa\\qa_results.json")
    finally:
        if os.path.exists(pid_file):
            os.remove(pid_file)

if __name__ == "__main__":
    login()
    run()
