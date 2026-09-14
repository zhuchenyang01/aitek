<template>
  <div class="about">
    <h1>This is an about page</h1>
  </div>
</template>

<template>
  <div>
    <h2>测试前后端连通</h2>
    <div>{{resData}}</div>
  </div>
</template>

<script>
import axios from 'axios'
export default {
  data(){
    return{
      resData:''
    }
  },
  mounted(){
    //页面加载完成就请求后端
    axios.get('/api/test/')
    .then(res=>{
      console.log('成功',res.data)
      this.resData = res.data
    })
    .catch(err=>{
      console.log('请求失败',err)
    })
  }
}
</script>
