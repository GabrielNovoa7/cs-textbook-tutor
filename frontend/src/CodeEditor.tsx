import { lazy, Suspense } from "react";
import type { EditorProps } from "@monaco-editor/react";

const LocalEditor = lazy(() => import("./LocalCodeEditor"));

export default function CodeEditor(props: EditorProps) {
  return <Suspense fallback={<p role="status">Loading code editor…</p>}>
    <LocalEditor {...props} />
  </Suspense>;
}
