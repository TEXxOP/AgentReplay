/**
 * ControlPanel — Agent selector, task input, run button
 */

export function renderControlPanel(container) {
  container.classList.add('panel');
  container.innerHTML = `
    <div class="panel-header">
      <span class="panel-title"><i data-lucide="zap" class="inline-icon"></i> Launch Agent</span>
    </div>
    <div class="panel-body">
      <div class="agent-selector">
        <button class="agent-btn active" data-agent="research" id="btn-agent-research">
          <i data-lucide="search" class="inline-icon"></i> Research
        </button>
        <button class="agent-btn" data-agent="debug" id="btn-agent-debug">
          <i data-lucide="bug" class="inline-icon"></i> Debug
        </button>
      </div>
      <textarea
        class="task-input"
        id="task-input"
        placeholder="Enter a task for the agent...&#10;e.g. 'Research quantum computing security'&#10;or 'Debug the off_by_one error in find_max'"
      ></textarea>
      <button class="run-btn" id="run-btn">
        <i data-lucide="play" class="inline-icon"></i> Run & Record
      </button>
    </div>
  `;

  // Agent selection
  container.querySelectorAll('.agent-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      container.querySelectorAll('.agent-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      window.__state.selectedAgent = btn.dataset.agent;

      // Update placeholder
      const input = document.getElementById('task-input');
      if (btn.dataset.agent === 'research') {
        input.placeholder = "Enter a research topic...\ne.g. 'Research AI security vulnerabilities'";
      } else {
        input.placeholder = "Describe the bug...\ne.g. 'Debug the off_by_one error in find_max function'";
      }
    });
  });

  // Run button
  document.getElementById('run-btn').addEventListener('click', async () => {
    const task = document.getElementById('task-input').value.trim();
    if (!task) {
      document.getElementById('task-input').focus();
      return;
    }

    const btn = document.getElementById('run-btn');
    btn.disabled = true;
    btn.innerHTML = '<span class="loading-spinner"></span> Running...';

    try {
      await window.__runAgent(window.__state.selectedAgent, task);
    } catch (e) {
      console.error(e);
    }

    btn.disabled = false;
    btn.innerHTML = '<i data-lucide="play" class="inline-icon"></i> Run & Record';
    if (window.lucide) window.lucide.createIcons();
  });
}
