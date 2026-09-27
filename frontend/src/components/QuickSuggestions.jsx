// Situation-first entry points. Keep requests within the real Co.opSmile catalog.
const SCENARIOS = [
  {
    icon: '🧺',
    title: 'Sắp hết đồ giặt giũ',
    detail: 'Tìm nhanh nước giặt phù hợp',
    prompt: 'Tôi sắp hết nước giặt và cần mua gấp. Gợi ý vài lựa chọn phù hợp trong catalog, ưu tiên loại dễ dùng cho gia đình.',
  },
  {
    icon: '🪥',
    title: 'Thiếu đồ vệ sinh cá nhân',
    detail: 'Chọn kem đánh răng theo nhu cầu',
    prompt: 'Tôi cần mua kem đánh răng ngay. Hãy gợi ý vài lựa chọn trong catalog và giúp tôi chọn nhanh.',
  },
  {
    icon: '🏠',
    title: 'Cần xử lý việc nhà',
    detail: 'Tìm sản phẩm chăm sóc nhà cửa',
    prompt: 'Tôi cần mua sản phẩm chăm sóc nhà cửa gấp. Hãy xem catalog hiện có và hỏi tôi một câu nếu cần để chọn đúng món.',
  },
]
export default function QuickSuggestions({ onPick, disabled }) {
  return (
    <section className="rescue-intro" aria-labelledby="rescue-title">
      <div className="rescue-eyebrow"><span className="rescue-live-dot" /> TRỢ LÝ MUA NHANH</div>
      <h2 id="rescue-title">Cứu Gấp 30</h2>
      <p className="rescue-lead">Có việc gấp ở nhà? Chọn tình huống, để Chọn Đúng tìm sản phẩm phù hợp trong catalog Co.opSmile.</p>
      <div className="scenario-grid">
        {SCENARIOS.map((scenario) => (
          <button
            key={scenario.title}
            className="scenario-card"
            disabled={disabled}
            onClick={() => onPick(scenario.prompt)}
          >
            <span className="scenario-icon" aria-hidden="true">{scenario.icon}</span>
            <span className="scenario-copy"><strong>{scenario.title}</strong><small>{scenario.detail}</small></span>
            <span className="scenario-arrow" aria-hidden="true">→</span>
          </button>
        ))}
      </div>
      <div className="quick-suggestions-minimal">
        <div className="suggestions-hint">Hoặc bắt đầu bằng nhu cầu của bạn:</div>
        <div className="suggestions-chips">
          {['Kem đánh răng dịu nhẹ dưới 70 nghìn', 'Nước giặt cho máy cửa trước'].map((text) => (
            <button key={text} className="suggestion-chip" disabled={disabled} onClick={() => onPick(text)}>{text}</button>
          ))}
        </div>
      </div>
    </section>
  )
}


