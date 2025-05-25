<template>
  <div id="app">
    <Login v-if="!isLoggedIn" @login-success="handleLoginSuccess" />
    <div v-else class="container">
      <div class="dashboard">
        <DeploymentTool
            @deploy-success="handleDeploySuccess"
            :deployed-models="deployedModels"
            :auth-info="authInfo" />
        <DeployedModels
            :models="deployedModels"
            @remove="removeModel"
            :auth-info="authInfo" />
      </div>
      <div class="image-section">
        <MyImage />
      </div>
    </div>
  </div>
</template>

<script>
import Login from './components/Login.vue'
import DeploymentTool from './components/DeploymentTool.vue'
import MyImage from './components/MyImage.vue'
import DeployedModels from './components/DeployedModels.vue'

export default {
  name: 'App',
  components: {
    Login,
    DeploymentTool,
    MyImage,
    DeployedModels
  },
  data() {
    return {
      isLoggedIn: false,
      authInfo: {},
      deployedModels: []
    }
  },
  methods: {
    handleLoginSuccess(credentials) {
      this.authInfo = credentials
      this.isLoggedIn = true
    },
    handleDeploySuccess(modelData) {
      try {
        this.deployedModels.push({
          name: modelData.name,
          precision: modelData.precision,
          time: new Date().toLocaleString()
        })
      } catch (err) {
        this.$reportError(err, {
          action: 'handle_deploy_success',
          modelData: JSON.stringify(modelData)
        })
        this.$message.error('部署记录保存失败')
      }
    },
    removeModel(index) {
      try {
        this.deployedModels.splice(index, 1)
        this.$message.success('模型已移除')
      } catch (err) {
        this.$reportError(err, {
          action: 'remove_model',
          index: index
        })
        this.$message.error('模型移除失败')
      }
    },
    globalErrorHandler(err, vm, info) {
      this.$reportError(err, {
        component: vm?.$options?.name,
        lifecycleHook: info,
        stack: err.stack
      })
      console.error('全局捕获的错误:', err)
    }
  },
  mounted() {
    // 注册未处理的Promise rejection
    window._unhandledRejection = (event) => {
      this.$reportError(event.reason, {
        type: 'unhandled_rejection'
      })
    }
    window.addEventListener('unhandledrejection', window._unhandledRejection)
  },
  beforeUnmount() {
    if (window._unhandledRejection) {
      window.removeEventListener('unhandledrejection', window._unhandledRejection)
    }
  }
}
</script>

<style>
body {
  font-family: "Helvetica Neue", Helvetica, "PingFang SC", "Hiragino Sans GB", Arial, sans-serif;
  margin: 0;
  padding: 20px;
  background-color: #f5f7fa;
}

.container {
  max-width: 95%;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.dashboard {
  display: flex;
  gap: 20px;
  flex-wrap: wrap;
}

.dashboard > *:first-child {
  flex: 2;
  min-width: 800px; /* 设置最小宽度 */
}

.dashboard > *:last-child {
  flex: 1;
  min-width: 300px; /* 保持 DeployedModels 的最小宽度 */
}

/*  MyImage 居中 */
.image-section {
  display: flex;
  justify-content: center;
}
</style>