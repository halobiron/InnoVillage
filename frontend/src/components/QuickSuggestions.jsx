// Simple, elegant quick-start suggestion chips
const SUGGESTIONS = [
  'Kem đánh răng dịu nhẹ dưới 70 nghìn',
  'Combo nước giặt và nước rửa chén cho gia đình',
]
export default function QuickSuggestions({ onPick, disabled }) {
  return (
    <div className="quick-suggestions-minimal">
      <div className="suggestions-hint">Gợi ý câu hỏi nhanh:</div>
      <div className="suggestions-chips">
        {SUGGESTIONS.map((text, idx) => (
          <button
            key={idx}
            className="suggestion-chip"
            disabled={disabled}
            onClick={() => onPick(text)}
          >
            {text}
          </button>
        ))}
      </div>
    </div>
  )
}


