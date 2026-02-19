"use client";

import { useIAStore } from "@/lib/stores/ia-store";
import { IASessionPicker } from "./IASessionPicker";
import { IAEditor } from "./IAEditor";

export function IAWorkspace() {
  const { activeSessionId, setActiveSessionId, reset } = useIAStore();

  if (activeSessionId) {
    return (
      <IAEditor
        sessionId={activeSessionId}
        onBack={() => reset()}
      />
    );
  }

  return <IASessionPicker onSelectSession={setActiveSessionId} />;
}
