module.exports = {
  publicPath: '/',
  devServer: {
    host: '0.0.0.0',
    port: 8081,
    proxy: {
      '/api/': {
        target: 'http://127.0.0.1:8001',
        changeOrigin: true,
      },
      '/media/': {
        target: 'http://127.0.0.1:8001',
        changeOrigin: true,
      },
    },
  },
}
