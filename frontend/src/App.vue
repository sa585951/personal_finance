<template>
  <Navbar v-if="!['Login', 'AuthCallback'].includes($route.name)" />
  <main :class="{ 'with-navbar': !['Login', 'AuthCallback'].includes($route.name) }">
  <router-view />
  </main>
</template>

<script>
import Navbar from './components/shared/Navbar.vue';

export default {
  name: 'App',
  components: {
    Navbar,
  },
};
</script>

<style>
@media (min-width: 1024px) {
  #app main.with-navbar { padding-top: 72px; }
}
</style>
