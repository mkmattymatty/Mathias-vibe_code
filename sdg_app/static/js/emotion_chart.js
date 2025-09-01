async function loadMoodChart() {
  try {
    const r = await fetch('/api/emotions');
    const data = await r.json();
    const ctx = document.getElementById('moodChart');
    if (!ctx) return;
    const chart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: data.labels,
        datasets: [{
          label: 'Mood Index (pos - neg)',
          data: data.scores,
          borderWidth: 2,
          fill: false,
          tension: 0.2
        }]
      },
      options: {
        responsive: true,
        scales: {
          y: { beginAtZero: true, suggestedMin: -1, suggestedMax: 1 }
        }
      }
    });

    // Prompt question based on trend
    const last = data.scores[data.scores.length - 1] || 0;
    const prompt = document.getElementById('supportPrompt');
    if (prompt) {
      if (last < 0) {
        prompt.textContent = 'Can you tell us how to help?';
      } else {
        prompt.textContent = 'Nice trend! Anything we can support you with?';
      }
    }
  } catch (e) {
    console.error(e);
  }
}
