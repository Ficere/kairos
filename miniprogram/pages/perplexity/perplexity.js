const api = require('../../utils/api')

Page({
  data: {
    loading: true,
    suggestions: [],
    availableDates: [],
    selectedDate: '',
    selectedIndex: -1,
    showDetail: false
  },

  onLoad() {
    this.loadDates()
  },

  onPullDownRefresh() {
    this.loadData().then(() => wx.stopPullDownRefresh())
  },

  async loadDates() {
    try {
      const res = await api.getPerplexityDates()
      const dates = res.dates || []
      this.setData({ availableDates: dates })
      if (dates.length > 0) {
        this.setData({ selectedDate: dates[0] })
        this.loadData()
      } else {
        this.setData({ loading: false })
      }
    } catch (e) {
      wx.showToast({ title: '加载日期失败', icon: 'none' })
      this.setData({ loading: false })
    }
  },

  async loadData() {
    if (!this.data.selectedDate) return
    this.setData({ loading: true })
    try {
      const res = await api.getPerplexity(this.data.selectedDate)
      this.setData({
        suggestions: res.suggestions || [],
        loading: false
      })
    } catch (e) {
      wx.showToast({ title: e.message || '加载失败', icon: 'none' })
      this.setData({ loading: false })
    }
  },

  onDateChange(e) {
    const index = e.detail.value
    const date = this.data.availableDates[index]
    this.setData({ selectedDate: date, selectedIndex: -1, showDetail: false })
    this.loadData()
  },

  onItemTap(e) {
    const index = e.currentTarget.dataset.index
    this.setData({
      selectedIndex: index,
      showDetail: true
    })
  },

  onCloseDetail() {
    this.setData({ showDetail: false })
  },

  getDirectionClass(direction) {
    if (direction.includes('做多') || direction.includes('偏多')) return 'tag-long'
    if (direction.includes('做空') || direction.includes('逢高')) return 'tag-short'
    if (direction.includes('止损')) return 'tag-warn'
    return 'tag-wait'
  },

  getDirectionIcon(direction) {
    if (direction.includes('做多') || direction.includes('偏多')) return '🟢'
    if (direction.includes('做空') || direction.includes('逢高')) return '🔴'
    if (direction.includes('止损')) return '⚠️'
    return '⚪'
  }
})

