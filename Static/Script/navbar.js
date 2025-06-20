// Function to highlight the active nav link based on the current path
// Get current path
  const currentPath = window.location.pathname;

  // Get all the nav links
  const navLinks = document.querySelectorAll('.item-title');

  navLinks.forEach(link => {
    // Check if link's href ends with the current path
    if (link.getAttribute('href') === currentPath) {
      link.classList.add('active');
    }
  });

  