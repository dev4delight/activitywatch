/**
 * Employee Selector Enhancement for ActivityWatch
 * Adds an employee dropdown next to the date selector in Activity view
 * This is an admin feature for viewing different employees' activity data
 */
(function() {
  'use strict';

  let employees = [];
  let selectedEmployeeId = localStorage.getItem('selectedEmployeeId') || '';
  let initialized = false;
  let lastInsertedPath = '';

  // Fetch employees from API
  async function loadEmployees() {
    try {
      const response = await fetch('/api/0/admin/employees');
      const data = await response.json();
      employees = data.employees || [];
      console.log('Employee selector: Loaded', employees.length, 'employees');
      return employees;
    } catch (error) {
      console.log('Employee selector: No employees API available');
      return [];
    }
  }

  // Get selected employee ID (for use by other scripts)
  window.getSelectedEmployeeId = function() {
    return selectedEmployeeId || null;
  };

  // Create the employee selector dropdown (matching ActivityWatch's Bootstrap style)
  function createEmployeeSelector() {
    const container = document.createElement('div');
    container.id = 'employee-selector-container';
    container.className = 'mx-2';
    container.style.cssText = 'display: flex; align-items: center;';

    container.innerHTML = `
      <div class="input-group" style="min-width: 180px;">
        <div class="input-group-prepend">
          <span class="input-group-text" style="
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            font-size: 12px;
            padding: 6px 10px;
          ">
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-right: 4px;">
              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
              <circle cx="12" cy="7" r="4"></circle>
            </svg>
            Employee
          </span>
        </div>
        <select id="employee-activity-dropdown" class="form-control" style="
          font-size: 13px;
          padding: 6px 10px;
          border-color: #667eea;
          cursor: pointer;
        ">
          <option value="">All Employees</option>
        </select>
      </div>
    `;
    return container;
  }

  // Update dropdown with employees
  function updateDropdown() {
    const dropdown = document.getElementById('employee-activity-dropdown');
    if (!dropdown) return;

    dropdown.innerHTML = '<option value="">All Employees</option>';

    employees.forEach(emp => {
      const option = document.createElement('option');
      option.value = emp.id;
      const hours = emp.total_hours || 0;
      const hoursText = hours > 0 ? ` - ${hours.toFixed(1)}h` : '';
      option.textContent = `${emp.name || emp.id}${hoursText}`;
      if (emp.id === selectedEmployeeId) {
        option.selected = true;
      }
      dropdown.appendChild(option);
    });
  }

  // Handle employee selection change
  function onEmployeeChange(event) {
    const newEmployeeId = event.target.value || '';

    if (newEmployeeId === selectedEmployeeId) return;

    selectedEmployeeId = newEmployeeId;

    if (selectedEmployeeId) {
      localStorage.setItem('selectedEmployeeId', selectedEmployeeId);
    } else {
      localStorage.removeItem('selectedEmployeeId');
    }

    console.log('Employee selected:', selectedEmployeeId || 'All');

    // Find the selected employee and navigate to their device's hostname
    if (selectedEmployeeId) {
      const emp = employees.find(e => e.id === selectedEmployeeId);
      if (emp && emp.devices && emp.devices.length > 0) {
        const hostname = emp.devices[0].hostname || emp.devices[0].id;
        const currentHash = window.location.hash || '';

        // Parse current activity URL and replace hostname
        const activityMatch = currentHash.match(/#\/activity\/([^\/]+)(\/.*)?/);
        if (activityMatch) {
          const restOfPath = activityMatch[2] || '/day';
          window.location.hash = `#/activity/${hostname}${restOfPath}`;
          return;
        }
      }
    }

    // If no specific navigation, just reload to refresh with new filter
    window.location.reload();
  }

  // Find and insert the selector next to the date input in Activity view
  function insertIntoActivityView() {
    const currentHash = window.location.hash || '';

    // Only show on activity pages
    if (!currentHash.includes('/activity/')) {
      removeSelector();
      return false;
    }

    // Check if already inserted for this path
    if (document.getElementById('employee-selector-container')) {
      return true;
    }

    // Find the date input or period selector row
    // Looking for the div that contains the date picker and period selector
    const dateInput = document.querySelector('input[type="date"]');
    const periodSelector = document.querySelector('.b-form-select, select.form-control');

    // Find the parent flex container that has the date controls
    let targetContainer = null;

    // Try to find the main control row (div.mb-2.d-flex)
    const controlRows = document.querySelectorAll('div.d-flex');
    for (const row of controlRows) {
      // Check if this row contains navigation buttons or date input
      if (row.querySelector('input[type="date"]') ||
          row.querySelector('.input-group') ||
          row.querySelector('button[class*="outline-dark"]')) {
        targetContainer = row;
        break;
      }
    }

    if (!targetContainer) {
      // Fallback: try to find by looking for the date input's parent
      if (dateInput) {
        targetContainer = dateInput.closest('.d-flex');
      }
    }

    if (!targetContainer) {
      console.log('Employee selector: Target container not found, retrying...');
      return false;
    }

    // Create and insert the selector
    const selector = createEmployeeSelector();

    // Insert after the date input div (mx-2) or at position 2 (after period selector)
    const dateInputDiv = targetContainer.querySelector('div.mx-2');
    if (dateInputDiv) {
      dateInputDiv.after(selector);
    } else {
      // Insert before the ml-auto buttons (filter/refresh)
      const mlAutoDiv = targetContainer.querySelector('.ml-auto');
      if (mlAutoDiv) {
        mlAutoDiv.before(selector);
      } else {
        targetContainer.appendChild(selector);
      }
    }

    // Update dropdown and add listener
    updateDropdown();
    const dropdown = document.getElementById('employee-activity-dropdown');
    if (dropdown) {
      dropdown.addEventListener('change', onEmployeeChange);
    }

    lastInsertedPath = currentHash;
    console.log('Employee selector: Inserted into Activity view');
    return true;
  }

  // Remove selector if not on activity page
  function removeSelector() {
    const existing = document.getElementById('employee-selector-container');
    if (existing) {
      existing.remove();
    }
  }

  // Add admin indicator badge next to the selector
  function addAdminBadge() {
    if (employees.length === 0) return;

    const container = document.getElementById('employee-selector-container');
    if (!container || container.querySelector('.admin-badge')) return;

    const badge = document.createElement('span');
    badge.className = 'admin-badge badge badge-info ml-2';
    badge.style.cssText = 'font-size: 10px; padding: 3px 6px;';
    badge.textContent = 'Admin Mode';
    container.appendChild(badge);
  }

  // Initialize the employee selector
  async function init() {
    if (initialized) return;

    // Wait for the page to be ready
    await new Promise(resolve => {
      if (document.readyState === 'complete') {
        resolve();
      } else {
        window.addEventListener('load', resolve);
      }
    });

    // Wait a bit for Vue to mount
    await new Promise(resolve => setTimeout(resolve, 800));

    // Load employees
    const emps = await loadEmployees();
    if (emps.length === 0) {
      console.log('Employee selector: No employees found, admin mode disabled');
      return;
    }

    initialized = true;

    // Try to insert into activity view
    insertIntoActivityView();

    // Watch for hash changes (Vue router navigation)
    window.addEventListener('hashchange', () => {
      setTimeout(() => {
        insertIntoActivityView();
      }, 300);
    });

    // Watch for DOM changes (Vue might re-render the activity view)
    const observer = new MutationObserver((mutations) => {
      const currentHash = window.location.hash || '';
      if (currentHash.includes('/activity/')) {
        if (!document.getElementById('employee-selector-container')) {
          setTimeout(() => insertIntoActivityView(), 100);
        }
      }
    });

    observer.observe(document.body, {
      childList: true,
      subtree: true
    });

    // Periodic check to ensure selector is present on activity pages
    setInterval(() => {
      const currentHash = window.location.hash || '';
      if (currentHash.includes('/activity/') && !document.getElementById('employee-selector-container')) {
        insertIntoActivityView();
      }
    }, 2000);

    console.log('Employee selector: Initialized with', emps.length, 'employees');
  }

  // Run initialization
  init();
})();
