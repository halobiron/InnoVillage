import { useEffect, useMemo, useState } from 'react'
import { getRefillOptions, getRefillQuote } from '../api'

const formatVnd = (value) => `${Number(value).toLocaleString('vi-VN')}đ`

export default function RefillDemo() {
  const [open, setOpen] = useState(false)
  const [options, setOptions] = useState(null)
  const [preferredSku, setPreferredSku] = useState('')
  const [sku, setSku] = useState('')
  const [quantityKg, setQuantityKg] = useState(1)
  const [address, setAddress] = useState('')
  const [quote, setQuote] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [submitted, setSubmitted] = useState(false)

  useEffect(() => {
    function handleOpen(event) {
      setPreferredSku(event.detail?.sku || '')
      setQuote(null)
      setError('')
      setSubmitted(false)
      setOpen(true)
    }
    window.addEventListener('open-refill-demo', handleOpen)
    return () => window.removeEventListener('open-refill-demo', handleOpen)
  }, [])

  useEffect(() => {
    if (!open || options) return
    setLoading(true)
    getRefillOptions()
      .then((data) => {
        setOptions(data)
        setSku(data.products.some((product) => product.sku === preferredSku)
          ? preferredSku
          : data.products[0]?.sku || '')
        setQuantityKg(data.quantities_kg[0] || 1)
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [open, options, preferredSku])

  useEffect(() => {
    if (options?.products.some((product) => product.sku === preferredSku)) {
      setSku(preferredSku)
      setQuote(null)
    }
  }, [options, preferredSku])

  const selected = useMemo(() => options?.products.find((product) => product.sku === sku), [options, sku])

  async function calculateQuote(event) {
    event.preventDefault()
    setLoading(true)
    setError('')
    setSubmitted(false)
    try {
      const result = await getRefillQuote({ sku, quantityKg, address })
      setQuote(result)
    } catch (err) {
      setError(err.message)
      setQuote(null)
    } finally {
      setLoading(false)
    }
  }

  if (!open) return null

  return (
    <div className="refill-demo">
        <div className="refill-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setOpen(false) }}>
          <section className="refill-flow" role="dialog" aria-modal="true" aria-labelledby="refill-title">
          <header className="refill-dialog-head">
            <div className="refill-demo-copy">
              <span className="refill-icon" aria-hidden="true">♻️</span>
              <div>
                <h3 id="refill-title">Trạm refill di động</h3>
              <p>Dùng giá sản phẩm nước giặt dạng túi trong catalog để mô phỏng nạp đầy chai cũ.</p>
              </div>
            </div>
            <button className="refill-close-btn" type="button" onClick={() => setOpen(false)} aria-label="Đóng demo refill">×</button>
          </header>
          <div className="refill-demo-notice">{options?.notice || 'Đang tải dữ liệu demo…'}</div>
          {loading && !options ? <p className="refill-feedback">Đang tải sản phẩm…</p> : null}
          {selected && <p className="refill-prefilled">Sản phẩm đang chọn: <strong>{selected.name}</strong></p>}
          {options?.products?.length > 0 && !submitted && (
            <form className="refill-form" onSubmit={calculateQuote}>
              <label>Sản phẩm tham chiếu từ catalog
                <select value={sku} onChange={(event) => { setSku(event.target.value); setQuote(null) }}>
                  {options.products.map((product) => <option key={product.sku} value={product.sku}>{product.name} · {formatVnd(product.catalog_price_vnd)}</option>)}
                </select>
              </label>
              {selected && <p className="refill-source-link">Giá catalog {formatVnd(selected.catalog_price_vnd)} / gói {selected.catalog_package_kg}kg · <a href={selected.catalog_url} target="_blank" rel="noreferrer">Xem nguồn</a></p>}
              <label>Lượng nạp mô phỏng
                <select value={quantityKg} onChange={(event) => { setQuantityKg(Number(event.target.value)); setQuote(null) }}>
                  {options.quantities_kg.map((value) => <option key={value} value={value}>{value} kg</option>)}
                </select>
              </label>
              <label>Địa chỉ giao demo
                <input value={address} onChange={(event) => { setAddress(event.target.value); setQuote(null) }} placeholder="Số nhà, đường, phường, quận" required minLength={8} />
              </label>
              <button className="refill-submit-btn" type="submit" disabled={loading || !sku}>{loading ? 'Đang tính…' : 'Tính giá & phí giao mô phỏng'}</button>
              {quote && <div className="refill-quote" aria-live="polite">
                <div><span>Nạp {quote.quantity_kg}kg · giảm demo 10%</span><strong>{formatVnd(quote.subtotal_vnd)}</strong></div>
                <div><span>Phí giao demo</span><strong>{formatVnd(quote.delivery_fee_vnd)}</strong></div>
                <div className="refill-total"><span>Tổng mô phỏng</span><strong>{formatVnd(quote.total_vnd)}</strong></div>
                <p>Thời gian giao {quote.eta_minutes} phút và phí giao là thông số giả lập cho demo.</p>
                <button className="refill-submit-btn" type="button" onClick={() => setSubmitted(true)}>Tạo đơn refill demo</button>
              </div>}
            </form>
          )}
          {submitted && <div className="refill-success" role="status"><strong>Đã tạo đơn refill mô phỏng!</strong><span>Đơn không được gửi cho Co.opSmile hay đơn vị giao hàng. Đây là bản demo luồng đặt dịch vụ.</span><button type="button" onClick={() => { setSubmitted(false); setQuote(null) }}>Tạo đơn demo khác</button></div>}
          {error && <p className="refill-error" role="alert">{error}</p>}
          {options && options.products.length === 0 && <p className="refill-feedback">Catalog hiện chưa có sản phẩm phù hợp để dựng demo refill.</p>}
          </section>
        </div>
    </div>
  )
}
