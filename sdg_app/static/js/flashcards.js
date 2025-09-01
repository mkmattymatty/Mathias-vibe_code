// Flip on click
document.addEventListener('click', (e) => {
  const card = e.target.closest('.flip-card');
  if (card) {
    card.classList.toggle('flipped');
  }
});

// "Don't slumber! Hey!" alert if user takes too long before flipping
// We start a timer per card and if not flipped within timeout -> alert.
document.querySelectorAll('.flip-card').forEach(card => {
  const timeoutSec = parseInt(card.dataset.timeout || '120', 10);
  let warned = false;
  setTimeout(() => {
    if (!card.classList.contains('flipped') && !warned) {
      warned = true;
      alert("Don't slumber! Hey!");
    }
  }, timeoutSec * 1000);
});
