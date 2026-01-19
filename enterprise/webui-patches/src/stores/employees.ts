import { defineStore } from 'pinia';
import axios from 'axios';

export interface IDevice {
  id: string;
  employee_id: string;
  hostname: string;
  device_type: string;
  os_info: string;
  last_seen: string;
  is_active: boolean;
}

export interface IEmployee {
  id: string;
  name: string;
  email: string;
  department: string;
  role: string;
  is_active: boolean;
  devices: IDevice[];
  stats: {
    event_count: number;
    total_hours: number;
  };
}

interface State {
  employees: IEmployee[];
  selectedEmployeeId: string | null;
  loaded: boolean;
}

export const useEmployeesStore = defineStore('employees', {
  state: (): State => ({
    employees: [],
    selectedEmployeeId: null,
    loaded: false,
  }),

  getters: {
    selectedEmployee(state): IEmployee | null {
      if (!state.selectedEmployeeId) return null;
      return state.employees.find(e => e.id === state.selectedEmployeeId) || null;
    },

    selectedEmployeeHostnames(state): string[] {
      const emp = this.selectedEmployee;
      if (!emp) return [];
      return emp.devices.map(d => d.hostname || d.id);
    },

    // Get all unique hostnames from all employees' devices
    allHostnames(state): string[] {
      const hostnames = new Set<string>();
      state.employees.forEach(emp => {
        (emp.devices || []).forEach(d => {
          if (d.hostname) hostnames.add(d.hostname);
          if (d.id) hostnames.add(d.id);
        });
      });
      return Array.from(hostnames);
    },

    // Get employee by hostname
    getEmployeeByHostname(state): (hostname: string) => IEmployee | null {
      return (hostname: string) => {
        return state.employees.find(emp =>
          (emp.devices || []).some(d => d.hostname === hostname || d.id === hostname)
        ) || null;
      };
    },
  },

  actions: {
    async loadEmployees(): Promise<void> {
      try {
        const response = await axios.get('/api/0/admin/employees');
        this.employees = response.data.employees || [];
        this.loaded = true;

        // Restore selected employee from localStorage
        const savedId = localStorage.getItem('selectedEmployeeId');
        if (savedId && this.employees.find(e => e.id === savedId)) {
          this.selectedEmployeeId = savedId;
        }
      } catch (error) {
        console.error('Failed to load employees:', error);
        this.employees = [];
        this.loaded = true;
      }
    },

    async ensureLoaded(): Promise<void> {
      if (!this.loaded) {
        await this.loadEmployees();
      }
    },

    selectEmployee(employeeId: string | null): void {
      this.selectedEmployeeId = employeeId;
      if (employeeId) {
        localStorage.setItem('selectedEmployeeId', employeeId);
      } else {
        localStorage.removeItem('selectedEmployeeId');
      }
    },

    // Check if a hostname belongs to the selected employee
    isHostnameAllowed(hostname: string): boolean {
      // If no employee selected, allow all
      if (!this.selectedEmployeeId) return true;

      const emp = this.selectedEmployee;
      if (!emp) return true;

      // Check if hostname matches any of the employee's devices
      return (emp.devices || []).some(d => d.hostname === hostname || d.id === hostname);
    },
  },
});
