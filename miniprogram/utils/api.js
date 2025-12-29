/**
 * API 请求工具
 */
const app = getApp()

/**
 * 发起 API 请求
 */
function request(path, options = {}) {
  return new Promise((resolve, reject) => {
    wx.request({
      url: `${app.globalData.apiBase}${path}`,
      method: options.method || 'GET',
      data: options.data || {},
      header: { 'Content-Type': 'application/json' },
      success: (res) => {
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data)
        } else {
          reject(new Error(res.data?.detail || '请求失败'))
        }
      },
      fail: (err) => {
        reject(new Error(err.errMsg || '网络错误'))
      }
    })
  })
}

/**
 * 获取分析结果
 */
function getResults(date, direction) {
  let path = '/api/results'
  const params = []
  if (date) params.push(`date=${date}`)
  if (direction && direction !== '总计') params.push(`direction=${direction}`)
  if (params.length) path += '?' + params.join('&')
  return request(path)
}

/**
 * 获取可用日期列表
 */
function getDates() {
  return request('/api/dates')
}

/**
 * 获取品种详情
 */
function getDetail(contract, date) {
  let path = `/api/detail/${contract}`
  if (date) path += `?date=${date}`
  return request(path)
}

/**
 * 获取有 Perplexity 分析的日期列表
 */
function getPerplexityDates() {
  return request('/api/perplexity/dates')
}

/**
 * 获取 Perplexity 分析结果
 */
function getPerplexity(date) {
  let path = '/api/perplexity'
  if (date) path += `?date=${date}`
  return request(path)
}

module.exports = {
  request,
  getResults,
  getDates,
  getDetail,
  getPerplexityDates,
  getPerplexity
}

