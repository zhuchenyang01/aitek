import Vue from 'vue'
import Vuex from 'vuex'
import system from './modules/system'
import aiTestcase from './modules/aiTestcase'
import aiApiTest from './modules/aiApiTest'
import aiWebTest from './modules/aiWebTest'
import aiAppTest from './modules/aiAppTest'
import ci from './modules/ci'
import projectConfig from './modules/projectConfig'

Vue.use(Vuex)

export default new Vuex.Store({
  modules: {
    system,
    aiTestcase,
    aiApiTest,
    aiWebTest,
    aiAppTest,
    ci,
    projectConfig
  }
})
