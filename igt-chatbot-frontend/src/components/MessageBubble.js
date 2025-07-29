export default function MessageBubble({ message }) {
  const isUser = message.role === 'user';

  // Function to detect and format code blocks
  const formatMessageContent = (content) => {
    if (!content) return content;

    // Split content by code block markers
    const parts = content.split(/(```[\s\S]*?```|`[^`]*`)/);
    
    return parts.map((part, index) => {
      // Multi-line code block (```...```)
      if (part.startsWith('```') && part.endsWith('```')) {
        const code = part.slice(3, -3);
        const language = code.split('\n')[0].trim();
        const codeContent = code.split('\n').slice(1).join('\n');
        return (
          <div key={index} className="code-block">
            {language && <div className="code-language">{language}</div>}
            <pre className="code-content">
              <code>{codeContent}</code>
            </pre>
          </div>
        );
      }
      // Inline code (`...`)
      else if (part.startsWith('`') && part.endsWith('`')) {
        const code = part.slice(1, -1);
        return <code key={index} className="inline-code">{code}</code>;
      }
      // Regular text
      else {
        return <span key={index}>{part}</span>;
      }
    });
  };

  return (
    <div className={`bubble-row ${isUser ? 'right' : 'left'}`}> 
      {message.role === 'assistant' && (
        <div className="avatar bot-avatar">
          <span role="img" aria-label="bot">🤖</span>
        </div>
      )}
      {isUser ? (
        <div className={`message-bubble user`}>{message.content}</div>
      ) : (
        message.answer_html ? (
          <div className={`message-bubble assistant`} dangerouslySetInnerHTML={{ __html: message.answer_html }} />
        ) : (
          <div className={`message-bubble assistant`}>
            {formatMessageContent(message.content)}
          </div>
        )
      )}
      {isUser && (
        <div className="avatar user-avatar">
          <span role="img" aria-label="user">🧑</span>
        </div>
      )}
    </div>
  );
}
