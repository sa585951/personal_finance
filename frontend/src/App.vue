<template>
  <Navbar v-if="!['Login', 'AuthCallback'].includes($route.name)" />
  <main>
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

<style></style>
