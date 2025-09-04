<template>
  <nav class="navbar">
    <div class="logo">
      <router-link to="/">財務管理</router-link>
    </div>
    <ul class="nav-links">
      <li>
        <router-link to="/">首頁</router-link>
      </li>
      <li>
        <router-link to="/assets">資產</router-link>
      </li>
      <li>
        <router-link to="/transactions">收支</router-link>
      </li>
      <li>
        <router-link to="/budgets">預算</router-link>
      </li>
      <li>
        <router-link to="/goals">目標</router-link>
      </li>
    </ul>
  </nav>
</template>

<script>
export default {
  name: 'Navbar',
};
</script>

<style scoped>
.navbar {
  background-color: var(--card-bg);
  padding: 1rem 2rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.logo a {
  font-weight: bold;
  font-size: 1.5rem;
  color: var(--primary-color);
  text-decoration: none;
}

.nav-links {
  list-style: none;
  display: flex;
  gap: 2rem;
}

.nav-links a {
  color: var(--text-color);
  text-decoration: none;
  font-weight: 500;
  transition: color 0.3s ease;
}

.nav-links a:hover,
.nav-links a.router-link-active {
  color: var(--primary-color);
  border-bottom: 2px solid var(--primary-color);
}
</style>