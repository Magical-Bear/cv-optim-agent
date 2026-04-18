<template>
  <el-config-provider>
    <div class="app-container">
      <header class="app-header">
        <h1 class="logo">CV Optim Agent</h1>
      </header>
      <main class="app-main">
        <router-view />
      </main>
    </div>
  </el-config-provider>
</template>

<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f0f2f5; }
.app-container { min-height: 100vh; display: flex; flex-direction: column; }
.app-header { background: #fff; border-bottom: 1px solid #e4e7ed; padding: 14px 32px; }
.logo { font-size: 20px; font-weight: 700; color: #409eff; }
.app-main { flex: 1; padding: 24px 16px; }
</style>
