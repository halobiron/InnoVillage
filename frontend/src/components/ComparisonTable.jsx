import { useState } from 'react'

function findCardForProduct(p, cards) {
  if (!cards || !cards.length) return null
  const clean = (s) => {
    if (!s) return ''
    return s
      .toLowerCase()
      .replace(/vì sao em đề xuất /g, '')
      .replace(/thông tin chi tiết: /g, '')
      .replace(/\?/g, '')
      .trim()
  }
  const target = clean(p)

  let match = cards.find((c) => clean(c.title) === target)
  if (match) return match

  match = cards.find((c) => clean(c.title).includes(target) || target.includes(clean(c.title)))
  if (match) return match

  return null
}

function CellBody({ cell }) {
  if (cell.status && cell.verdict) {
    return (
      <div className="verdict-box">
        <span className={`verdict-text status-${cell.status}`}>{cell.verdict}</span>
        {cell.detail ? <div className="verdict-detail">{cell.detail}</div> : null}
      </div>
    )
  }
  return (
    <div className="spec-box">
      <span className="spec-text">{cell.value != null ? cell.value : '—'}</span>
      {cell.is_best ? <span className="best-tag">Tốt nhất</span> : null}
    </div>
  )
}

function formatTradeoffLabel(label) {
  if (!label) return ''
  if (label.startsWith('Độ khớp với ví tiền')) {
    return 'Giá'
  }
  return label
}

function TradeoffPointsList({ points, type }) {
  if (!points || !points.length) {
    return <span className="tradeoff-none">—</span>
  }

  return (
    <ul className={`tradeoff-list tradeoff-${type}-list`}>
      {points.map((p, idx) => (
        <li key={`${p.label}-${idx}`} className="tradeoff-item">
          <span className="tradeoff-bullet" aria-hidden="true" />
          <span className="tradeoff-item-text">
            <strong className="tradeoff-item-label">{formatTradeoffLabel(p.label)}:</strong>{' '}
            <span className="tradeoff-item-val">{p.value}</span>
            {p.verdict ? (
              <span className={`tradeoff-pill pill-${type}`}>{p.verdict}</span>
            ) : null}
          </span>
        </li>
      ))}
    </ul>
  )
}

export default function ComparisonTable({ table, cards, blindMode = false, revealed = [], onReveal }) {
  const [showAllSpecs, setShowAllSpecs] = useState(false)
  if (!table || !table.products?.length || !table.rows?.length) return null
  const hasTradeoffs = table.tradeoffs?.length === table.products.length
  const hasStrengths = hasTradeoffs && table.tradeoffs.some((t) => t.strengths?.length > 0)
  const hasConsiderations = hasTradeoffs && table.tradeoffs.some((t) => t.considerations?.length > 0)

  // Bảng chính chỉ giữ giá + năm tiêu chí đầu mà model đã xếp theo nhu cầu.
  // Các field còn lại vẫn sẵn có, nhưng không lấn át quyết định mua.
  const primaryRows = table.rows.slice(0, 6)
  const extraRows = table.rows.slice(6)
  const displayedRows = showAllSpecs ? table.rows : primaryRows

  const renderRow = (row, ri) => (
    <tr key={`${row.label}-${ri}`}>
      <td className="td-sticky">
        <div className="crit-name">{row.label}</div>
        {row.better ? <div className="crit-hint">{row.better}</div> : null}
      </td>
      {row.cells.map((c, ci) => (
        <td
          key={ci}
          className={
            c.status
              ? `cell-status-${c.status}`
              : c.is_best
              ? 'cell-best'
              : ''
          }
        >
          {blindMode && /thương hiệu|nhãn hàng|model|mã sản phẩm|tên sản phẩm|tên hàng|product[_ ]?name/i.test(row.label) && !revealed.includes(ci)
            ? <span className="spec-text">Ẩn đến khi chọn</span>
            : <CellBody cell={c} />}
        </td>
      ))}
    </tr>
  )

  return (
    <div className="compare-container">
      <div className="compare-top">
        <h4 className="compare-title">Bảng so sánh ({table.products.length} sản phẩm)</h4>
        <span className="compare-scroll-hint">← Kéo ngang để xem đủ bảng →</span>
      </div>

      <div className="compare-table-wrapper">
        <table className="clean-table">
          <thead>
            <tr>
              <th className="th-sticky">Tiêu chí</th>
              {table.products.map((p, i) => {
                const card = findCardForProduct(p, cards)
                const priceLine = card?.lines?.find((l) => l.label === 'Giá')

                return (
                  <th key={i} className="th-product">
                    <div className="product-head">
                      {(!blindMode || revealed.includes(i)) && card?.image_url && (
                        <img src={card.image_url} alt={p} className="product-head-thumb" />
                      )}
                      <div className="product-head-title" title={blindMode && !revealed.includes(i) ? '' : p}>{blindMode && !revealed.includes(i) ? `Lựa chọn ${String.fromCharCode(65 + i)}` : p}</div>
                      {priceLine && <div className="product-head-price">{priceLine.value}</div>}
                      {blindMode && !revealed.includes(i) && <button className="blind-reveal-btn" onClick={() => onReveal?.(i)}>Chọn lựa chọn này</button>}
                    </div>
                  </th>
                )
              })}
            </tr>
          </thead>
          <tbody>
            {displayedRows.map(renderRow)}

            {extraRows.length > 0 && (
              <tr className="more-specs-tr">
                <td colSpan={table.products.length + 1}>
                  <button
                    type="button"
                    className="more-specs-btn"
                    onClick={() => setShowAllSpecs((current) => !current)}
                    aria-expanded={showAllSpecs}
                  >
                    {showAllSpecs
                      ? 'Thu gọn thông số'
                      : `Xem thêm ${extraRows.length} thông số`}
                  </button>
                </td>
              </tr>
            )}

            {hasStrengths && (
              <tr className="tradeoff-row strength-row">
                <td className="td-sticky td-tradeoff-header">
                  <div className="crit-name tradeoff-header-label strength-label">
                    <span className="tradeoff-header-dot dot-strength" />
                    Điểm mạnh
                  </div>
                  <div className="crit-hint">Ưu điểm nổi bật</div>
                </td>
                {table.tradeoffs.map((summary, i) => (
                  <td key={i} className="tradeoff-cell">
                    <TradeoffPointsList points={summary.strengths} type="strength" />
                  </td>
                ))}
              </tr>
            )}

            {hasConsiderations && (
              <tr className="tradeoff-row consideration-row">
                <td className="td-sticky td-tradeoff-header">
                  <div className="crit-name tradeoff-header-label consideration-label">
                    <span className="tradeoff-header-dot dot-consideration" />
                    Cần cân nhắc
                  </div>
                  <div className="crit-hint">Điểm cần lưu ý</div>
                </td>
                {table.tradeoffs.map((summary, i) => (
                  <td key={i} className="tradeoff-cell">
                    <TradeoffPointsList points={summary.considerations} type="consideration" />
                  </td>
                ))}
              </tr>
            )}

            <tr className="cta-tr">
              <td className="td-sticky"></td>
              {table.products.map((p, i) => {
                const card = findCardForProduct(p, cards)
                return (
                  <td key={i}>
                    {(!blindMode || revealed.includes(i)) && card && card.product_link ? (
                      <a
                        href={card.product_link}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="table-buy-btn"
                      >
                        Đặt mua
                      </a>
                    ) : null}
                  </td>
                )
              })}
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  )
}
