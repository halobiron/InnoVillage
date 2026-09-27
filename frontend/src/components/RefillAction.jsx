export default function RefillAction({ card }) {
  const productName = card?.title || ''
  const supported = Boolean(card?.sku && /nước giặt/i.test(productName))
  const reason = 'Demo refill hiện chỉ hỗ trợ các sản phẩm nước giặt dạng túi có trong catalog.'

  return (
    <button
      type="button"
      className={`refill-action${supported ? '' : ' unavailable'}`}
      disabled={!supported}
      title={supported ? 'Mở demo refill với sản phẩm này' : reason}
      aria-label={supported ? `Refill ${productName}` : `Chưa hỗ trợ refill: ${productName}`}
      onClick={() => window.dispatchEvent(new CustomEvent('open-refill-demo', { detail: { sku: card.sku } }))}
    >
      ♻ {supported ? 'Refill' : 'Chưa hỗ trợ'}
    </button>
  )
}
