import AssistantResponse from "./AssistantResponse";
import LoadingResponse from "./LoadingResponse";

export default function ChatMessageList({ messages, onOpenSources }) {
  return (
    <main className="chat">
      {messages.length === 0 && <p className="placeholder">Ask a research question to start.</p>}
      {messages.map((msg, index) => (
        <article key={msg.id || index} className={`bubble ${bubbleClass(msg.role)}`}>
          <div className="role">{labelForRole(msg.role)}</div>
          {msg.role === "assistant" && msg.payload ? (
            <AssistantResponse payload={msg.payload} onOpenSources={() => onOpenSources(msg.payload.report)} />
          ) : msg.role === "assistant-loading" ? (
            <LoadingResponse query={msg.query} progressMessages={msg.progressMessages} />
          ) : (
            <pre>{msg.text}</pre>
          )}
        </article>
      ))}
    </main>
  );
}

function bubbleClass(role) {
  if (role === "assistant-loading") return "assistant loading";
  if (role === "assistant") return "assistant";
  return "user";
}

function labelForRole(role) {
  if (role === "assistant-loading") return "Agent";
  if (role === "assistant") return "Agent";
  return "You";
}
