const api = require('../../utils/api')

Page({
  data: {
    loading: true,
    contract: '',
    date: '',
    detail: null
  },

  onLoad(options) {
    this.setData({
      contract: options.contract || '',
      date: options.date || ''
    })
    this.loadDetail()
  },

  async loadDetail() {
    const { contract, date } = this.data
    if (!contract) return

    this.setData({ loading: true })
    try {
      const res = await api.getDetail(contract, date)
      this.setData({ detail: res.data, loading: false })
      wx.setNavigationBarTitle({ title: `${res.data.name} 详情` })
    } catch (e) {
      wx.showToast({ title: e.message || '加载失败', icon: 'none' })
      this.setData({ loading: false })
    }
  },

  formatPrice(price) {
    return typeof price === 'number' ? price.toFixed(2) : price
  },

  formatIndicator(value) {
    return typeof value === 'number' ? value.toFixed(2) : (value || '-')
  }
})

