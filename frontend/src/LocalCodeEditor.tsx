import Editor, { loader } from "@monaco-editor/react";
import * as monaco from "monaco-editor/editor/editor.api.js";
import "monaco-editor/languages/definitions/java/register.js";
import "monaco-editor/languages/definitions/cpp/register.js";
import "monaco-editor/languages/definitions/python/register.js";
import EditorWorker from "monaco-editor/editor/editor.worker.js?worker";

// Bundle the editor and worker locally instead of requesting a blocked CDN script.
self.MonacoEnvironment = { getWorker: () => new EditorWorker() };
loader.config({ monaco });

export default Editor;
