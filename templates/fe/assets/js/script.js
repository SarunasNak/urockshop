// script.js

// Example: Alpine.js reactive state
document.addEventListener("alpine:init", () => {
  Alpine.data("dropdown", () => ({
    open: false,
    toggle() {
      this.open = !this.open;
    },
  }));
});

// Example: Initialize Swiper
document.addEventListener("DOMContentLoaded", () => {
  const swiper = new Swiper(".swiper", {
    loop: true,
    pagination: { el: ".swiper-pagination" },
    navigation: {
      nextEl: ".swiper-button-next",
      prevEl: ".swiper-button-prev",
    },
  });

  // Example: Headroom
  const header = document.querySelector(".header");
  if (header) {
    const headroom = new Headroom(header, {
      offset: 100,
      tolerance: {
        up: 0,
        down: 0,
      },
      classes: {
        initial: "header",
        pinned: "header--pinned",
        unpinned: "header--unpinned",
        top: "header--top",
        notTop: "header--scrolled border-brand-gray-medium",
        bottom: "header--bottom",
        notBottom: "header--not-bottom",
      },
      scroller: window,
    });
    headroom.init();
  }

  // Smooth scroll for anchor links
  document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
    anchor.addEventListener("click", function (e) {
      const href = this.getAttribute("href");

      // Skip if href is just "#" (like a modal trigger)
      if (!href || href === "#") return;

      const target = document.querySelector(href);
      if (target) {
        e.preventDefault();
        const yOffset = 0; // adjust for header height if needed
        const y =
          target.getBoundingClientRect().top + window.pageYOffset + yOffset;
        window.scrollTo({ top: y, behavior: "smooth" });
      }
    });
  });
});
