# Example Skiff plugin. Copy into ~/.skiff/plugins/ to enable.
TOOL_NAME = "word_count"
TOOL_DESC = "Count words/lines in a file"

def run(args):
    path = args.get("path", "")
    try:
        f = open(path, "r")
        try:
            content = f.read()
        finally:
            f.close()
        return {"ok": True, "words": len(content.split()), "lines": content.count("\n") + 1}
    except Exception as e:
        return {"ok": False, "error": str(e)}
