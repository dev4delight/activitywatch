<template lang="pug">
div(:class="{'fixed-top-padding': fixedTopMenu}")
  b-navbar.aw-navbar(toggleable="lg" :fixed="fixedTopMenu ? 'top' : null")
    // Brand on mobile
    b-navbar-nav.d-block.d-lg-none
      b-navbar-brand(to="/" style="background-color: transparent;")
        img.aligh-middle(src="/logo.png" style="height: 1.5em;")
        span.ml-2.align-middle(style="font-size: 1em; color: #000;") ActivityWatch

    b-navbar-toggle(target="nav-collapse")

    b-collapse#nav-collapse(is-nav)
      b-navbar-nav
        // Employee Selector Dropdown
        b-nav-item-dropdown.employee-selector(v-if="employees && employees.length > 0")
          template(slot="button-content")
            div.d-inline.px-2.px-lg-1
              icon(name="user")
              | {{ selectedEmployeeName }}
          b-dropdown-item(@click="selectEmployee(null)", :active="!selectedEmployeeId")
            icon(name="users")
            |  All Employees
          b-dropdown-divider
          b-dropdown-item(v-for="emp in employees", :key="emp.id", @click="selectEmployee(emp.id)", :active="selectedEmployeeId === emp.id")
            icon(name="user")
            |  {{ emp.name || emp.id }}
            small.text-muted.ml-2 ({{ emp.devices ? emp.devices.length : 0 }} device{{ emp.devices && emp.devices.length !== 1 ? 's' : '' }})

        // If only a single view (the default) is available
        b-nav-item(v-if="filteredActivityViews && filteredActivityViews.length === 1", v-for="view in filteredActivityViews", :key="view.name", :to="view.pathUrl")
          div.px-2.px-lg-1
            icon(name="calendar-day")
            | Activity

        // If multiple (or no) activity views are available
        b-nav-item-dropdown(v-if="!filteredActivityViews || filteredActivityViews.length !== 1")
          template(slot="button-content")
            div.d-inline.px-2.px-lg-1
              icon(name="calendar-day")
              | Activity
          b-dropdown-item(v-if="filteredActivityViews === null", disabled)
            span.text-muted Loading...
            br
          b-dropdown-item(v-else-if="filteredActivityViews && filteredActivityViews.length <= 0", disabled)
            | No activity reports available
            br
            small Make sure you have both an AFK and window watcher running
          b-dropdown-item(v-for="view in filteredActivityViews", :key="view.name", :to="view.pathUrl")
            icon(:name="view.icon")
            | {{ view.name }}

        b-nav-item(to="/timeline" style="font-color: #000;")
          div.px-2.px-lg-1
            icon(name="stream")
            | Timeline

        b-nav-item(to="/stopwatch")
          div.px-2.px-lg-1
            icon(name="stopwatch")
            | Stopwatch

      // Brand on large screens (centered)
      b-navbar-nav.abs-center.d-none.d-lg-block
        b-navbar-brand(to="/" style="background-color: transparent;")
          img.ml-0.aligh-middle(src="/logo.png" style="height: 1.5em;")
          span.ml-2.align-middle(style="font-size: 1.0em; color: #000;") ActivityWatch

      b-navbar-nav.ml-auto
        b-nav-item-dropdown
          template(slot="button-content")
            div.d-inline.px-2.px-lg-1
              icon(name="tools")
              | Tools
          b-dropdown-item(to="/search")
            icon(name="search")
            | Search
          b-dropdown-item(to="/trends" v-if="devmode")
            icon(name="chart-line")
            | Trends
          b-dropdown-item(to="/report" v-if="devmode")
            icon(name="chart-pie")
            | Report
          b-dropdown-item(to="/alerts" v-if="devmode")
            icon(name="flag-checkered")
            | Alerts
          b-dropdown-item(to="/timespiral" v-if="devmode")
            icon(name="history")
            | Timespiral
          b-dropdown-item(to="/query")
            icon(name="code")
            | Query
          b-dropdown-item(to="/graph" v-if="devmode")
            // TODO: use circle-nodes instead in the future
            icon(name="project-diagram")
            | Graph

        b-nav-item(to="/buckets")
          div.px-2.px-lg-1
            icon(name="database")
            | Raw Data
        b-nav-item(to="/settings")
          div.px-2.px-lg-1
            icon(name="cog")
            | Settings
</template>

<style lang="scss" scoped>
.fixed-top-padding {
  padding-bottom: 3.5em;
}
</style>

<script lang="ts">
// only import the icons you use to reduce bundle size
import 'vue-awesome/icons/calendar-day';
import 'vue-awesome/icons/calendar-week';
import 'vue-awesome/icons/stream';
import 'vue-awesome/icons/database';
import 'vue-awesome/icons/search';
import 'vue-awesome/icons/code';
import 'vue-awesome/icons/chart-line'; // TODO: switch to chart-column, when vue-awesome supports FA v6
import 'vue-awesome/icons/chart-pie';
import 'vue-awesome/icons/flag-checkered';
import 'vue-awesome/icons/stopwatch';
import 'vue-awesome/icons/cog';
import 'vue-awesome/icons/tools';
import 'vue-awesome/icons/history';

// TODO: use circle-nodes instead in the future
import 'vue-awesome/icons/project-diagram';
//import 'vue-awesome/icons/cicle-nodes';

import 'vue-awesome/icons/ellipsis-h';

import 'vue-awesome/icons/mobile';
import 'vue-awesome/icons/desktop';

// Employee selector icons
import 'vue-awesome/icons/user';
import 'vue-awesome/icons/users';

import _ from 'lodash';

import { mapState } from 'pinia';
import { useSettingsStore } from '~/stores/settings';
import { useBucketsStore } from '~/stores/buckets';
import { useEmployeesStore } from '~/stores/employees';
import { IBucket } from '~/util/interfaces';

export default {
  name: 'Header',
  data() {
    return {
      activityViews: null,
      employees: [],
      selectedEmployeeId: null,
      // Make configurable?
      fixedTopMenu: this.$isAndroid,
    };
  },
  computed: {
    ...mapState(useSettingsStore, ['devmode']),

    // Get the selected employee name for display
    selectedEmployeeName() {
      if (!this.selectedEmployeeId) return 'All Employees';
      const emp = this.employees.find(e => e.id === this.selectedEmployeeId);
      return emp ? (emp.name || emp.id) : 'All Employees';
    },

    // Filter activity views based on selected employee
    filteredActivityViews() {
      if (!this.activityViews) return null;
      if (!this.selectedEmployeeId) return this.activityViews;

      const emp = this.employees.find(e => e.id === this.selectedEmployeeId);
      if (!emp || !emp.devices || emp.devices.length === 0) return this.activityViews;

      // Get hostnames from employee's devices
      const employeeHostnames = emp.devices.map(d => d.hostname || d.id);

      // Filter views to only show devices belonging to selected employee
      return this.activityViews.filter(view =>
        employeeHostnames.includes(view.hostname)
      );
    },
  },
  methods: {
    selectEmployee(employeeId) {
      this.selectedEmployeeId = employeeId;
      // Save to localStorage
      if (employeeId) {
        localStorage.setItem('selectedEmployeeId', employeeId);
      } else {
        localStorage.removeItem('selectedEmployeeId');
      }
      // Update employees store
      const employeesStore = useEmployeesStore();
      employeesStore.selectEmployee(employeeId);
    },
  },
  mounted: async function () {
    // Load employees
    const employeesStore = useEmployeesStore();
    await employeesStore.loadEmployees();
    this.employees = employeesStore.employees;

    // Restore selected employee from localStorage
    const savedEmployeeId = localStorage.getItem('selectedEmployeeId');
    if (savedEmployeeId && this.employees.find(e => e.id === savedEmployeeId)) {
      this.selectedEmployeeId = savedEmployeeId;
    }

    // Load buckets and build activity views
    const bucketStore = useBucketsStore();
    await bucketStore.ensureLoaded();
    const buckets: IBucket[] = bucketStore.buckets;
    const types_by_host = {};

    const activityViews = [];

    // TODO: Change to use same bucket detection logic as get_buckets/set_available in store/modules/activity.ts
    _.each(buckets, v => {
      types_by_host[v.hostname] = types_by_host[v.hostname] || {};
      types_by_host[v.hostname].afk ||= v.type == 'afkstatus';
      types_by_host[v.hostname].window ||= v.type == 'currentwindow';
      // TODO: Use other bucket type ID in the future
      types_by_host[v.hostname].android ||= v.type == 'currentwindow' && v.id.includes('android');
    });
    //console.log(types_by_host);

    _.each(types_by_host, (types, hostname) => {
      if (types['android']) {
        activityViews.push({
          name: `${hostname} (Android)`,
          hostname: hostname,
          type: 'android',
          pathUrl: `/activity/${hostname}`,
          icon: 'mobile',
        });
      } else if (hostname != 'unknown') {
        activityViews.push({
          name: hostname,
          hostname: hostname,
          type: 'default',
          pathUrl: `/activity/${hostname}`,
          icon: 'desktop',
        });
      }
    });

    this.activityViews = activityViews;
  },
};
</script>

<style lang="scss" scoped>
@import '../style/globals';

.aw-navbar {
  background-color: white;
  border: solid $lightBorderColor;
  border-width: 0 0 1px 0;
}

.nav-item {
  align-items: center;

  margin-left: 0.2em;
  margin-right: 0.2em;
  border-radius: 0.5em;

  &:hover {
    background-color: #ddd;
  }
}

.abs-center {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
}

.employee-selector {
  background-color: #e3f2fd;
  border-radius: 0.5em;
  margin-right: 0.5em;

  &:hover {
    background-color: #bbdefb;
  }
}
</style>

<style lang="scss">
// Needed because dropdown somehow doesn't properly work with scoping
.nav-item {
  .nav-link {
    color: #555 !important;
  }
}

.employee-selector .dropdown-item.active {
  background-color: #1976d2;
  color: white;
}
</style>
