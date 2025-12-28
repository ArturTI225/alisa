document.addEventListener("DOMContentLoaded", () => {
  // Toasts: autoclose and manual close
  document.querySelectorAll(".alert").forEach((alert) => {
    const closeBtn = alert.querySelector(".alert-close");
    const dismiss = () => {
      alert.classList.add("hide");
      setTimeout(() => alert.remove(), 220);
    };
    let timer = setTimeout(dismiss, 5200);
    closeBtn?.addEventListener("click", dismiss);
    alert.addEventListener("mouseenter", () => clearTimeout(timer));
    alert.addEventListener("mouseleave", () => {
      if (!alert.classList.contains("hide")) {
        timer = setTimeout(dismiss, 2000);
      }
    });
  });

  // Notifications dropdown (fetch via API)
  const notifBell = document.getElementById("notif-bell");
  const notifPanel = document.getElementById("notif-panel");
  const notifCount = document.getElementById("notif-count");
  const notifList = document.getElementById("notif-list");
  const notifMarkAll = document.getElementById("notif-mark-all");

  async function fetchNotifs() {
    try {
      const res = await fetch("/api/notifications/");
      if (!res.ok) return;
      const data = await res.json();
      notifList.innerHTML = "";
      let unread = 0;
      data.forEach((n) => {
        if (!n.is_read) unread += 1;
        const item = document.createElement("div");
        item.className = "notif-item" + (n.is_read ? "" : " unread");
        item.innerHTML = `<strong>${n.title}</strong><p>${n.body || ""}</p>`;
        if (n.link) {
          item.addEventListener("click", () => {
            window.location.href = n.link;
          });
        }
        notifList.appendChild(item);
      });
      if (unread > 0) {
        notifCount.style.display = "grid";
        notifCount.textContent = unread;
      } else {
        notifCount.style.display = "none";
      }
    } catch (e) {
      console.warn("Notif fetch failed", e);
    }
  }

  notifBell?.addEventListener("click", () => {
    if (!notifPanel) return;
    if (notifPanel.style.display === "block") {
      notifPanel.style.display = "none";
      return;
    }
    notifPanel.style.display = "block";
    fetchNotifs();
  });

  notifMarkAll?.addEventListener("click", async (e) => {
    e.preventDefault();
    try {
      const res = await fetch("/api/notifications/", { method: "GET" });
      if (!res.ok) return;
      const data = await res.json();
      await Promise.all(
        data.filter((n) => !n.is_read).map((n) =>
          fetch(`/api/notifications/${n.id}/`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ is_read: true }),
          })
        )
      );
      fetchNotifs();
    } catch (err) {
      console.warn("Notif mark all failed", err);
    }
  });

  // Smooth scroll with Lenis (graceful fallback)
  if (window.Lenis) {
    const lenis = new Lenis({ lerp: 0.08, smooth: true });
    const raf = (time) => {
      lenis.raf(time);
      requestAnimationFrame(raf);
    };
    requestAnimationFrame(raf);
  }

  // Reveal fallback
  const revealTargets = document.querySelectorAll(".reveal");
  if (revealTargets.length) {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("visible");
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.14 }
    );
    revealTargets.forEach((el) => observer.observe(el));
    setTimeout(() => revealTargets.forEach((el) => el.classList.add("visible")), 300);
  }

  // Parallax on pointer move (skip static items)
  const parallaxItems = Array.from(document.querySelectorAll("[data-depth]")).filter((el) => !el.dataset.static);
  if (parallaxItems.length) {
    const handleMove = (event) => {
      const { clientX, clientY } = event;
      const { innerWidth, innerHeight } = window;
      const x = clientX / innerWidth - 0.5;
      const y = clientY / innerHeight - 0.5;
      parallaxItems.forEach((el) => {
        const depth = parseFloat(el.dataset.depth || "0.2");
        const translateX = x * depth * 40;
        const translateY = y * depth * 40;
        el.style.transform = `translate3d(${translateX}px, ${translateY}px, 0)`;
      });
    };
    window.addEventListener("pointermove", handleMove);
  }

  // Booking list filters
  const filterButtons = document.querySelectorAll("[data-booking-filter]");
  const bookingCards = document.querySelectorAll(".booking-card");
  const searchInput = document.getElementById("booking-search");
  const sortSelect = document.getElementById("booking-sort");
  let currentStatus = "all";

  const applyFilter = () => {
    const term = (searchInput?.value || "").toLowerCase().trim();
    bookingCards.forEach((card) => {
      const statusMatch = currentStatus === "all" || card.dataset.status === currentStatus;
      const searchMatch = !term || (card.dataset.search || "").toLowerCase().includes(term);
      card.classList.toggle("hidden", !(statusMatch && searchMatch));
    });
  };

  const applySort = () => {
    if (!sortSelect || !bookingCards.length) return;
    const dir = sortSelect.value;
    const parent = bookingCards[0].parentElement;
    const sorted = Array.from(bookingCards).sort((a, b) => {
      const da = Date.parse(a.dataset.date || "");
      const db = Date.parse(b.dataset.date || "");
      return dir === "asc" ? da - db : db - da;
    });
    sorted.forEach((el) => parent?.appendChild(el));
  };

  filterButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      filterButtons.forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      currentStatus = btn.dataset.bookingFilter || "all";
      applyFilter();
    });
  });

  searchInput?.addEventListener("input", () => {
    applyFilter();
  });

  sortSelect?.addEventListener("change", () => {
    applySort();
    applyFilter();
  });

  applySort();
  applyFilter();

  // 3D tilt on cards
  const tiltCards = document.querySelectorAll("[data-tilt]");
  tiltCards.forEach((card) => {
    card.addEventListener("pointermove", (e) => {
      const rect = card.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      const rotateY = ((x / rect.width) - 0.5) * 8;
      const rotateX = ((y / rect.height) - 0.5) * -8;
      card.style.transform = `perspective(900px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) translateZ(0)`;
    });
    card.addEventListener("pointerleave", () => {
      card.style.transform = "perspective(900px) rotateX(0deg) rotateY(0deg)";
    });
  });

  // GSAP animations
  if (window.gsap && window.ScrollTrigger) {
    gsap.registerPlugin(ScrollTrigger);

    gsap.from(".page", { opacity: 0, y: 20, duration: 0.6, ease: "power2.out" });

    // Hero entry
    gsap.from("#hero .hero-copy", {
      y: 40,
      opacity: 0,
      duration: 0.9,
      ease: "power3.out",
    });
    gsap.from("#hero .hero-card", {
      y: 60,
      opacity: 0,
      duration: 1.1,
      ease: "power3.out",
      delay: 0.2,
    });

    // Scroll-based reveals
    document.querySelectorAll(".section").forEach((section) => {
      gsap.from(section, {
        scrollTrigger: {
          trigger: section,
          start: "top 80%",
          toggleActions: "play none none reverse",
        },
        y: 60,
        opacity: 0,
        duration: 0.8,
        ease: "power3.out",
      });
    });

    // Staggered steps
    const staggered = document.querySelectorAll('[data-animate="stagger"]');
    if (staggered.length) {
      gsap.from(staggered, {
        scrollTrigger: {
          trigger: "#how",
          start: "top 75%",
        },
        y: 60,
        opacity: 0,
        stagger: 0.15,
        duration: 0.7,
        ease: "power2.out",
      });
    }

    // Cascade cards (services/providers)
    const cascades = document.querySelectorAll('[data-animate="cascade"]');
    if (cascades.length) {
      gsap.from(cascades, {
        scrollTrigger: {
          trigger: cascades[0].closest(".section") || cascades[0],
          start: "top 75%",
        },
        y: 40,
        opacity: 0,
        stagger: 0.08,
        duration: 0.6,
        ease: "power2.out",
      });
    }

    // Parallax on scroll using ScrollTrigger
    document.querySelectorAll("[data-depth]").forEach((el) => {
      const depth = parseFloat(el.dataset.depth || "0.2");
      gsap.to(el, {
        yPercent: depth * 30,
        ease: "none",
        scrollTrigger: {
          trigger: "#hero",
          start: "top top",
          end: "bottom top",
          scrub: true,
        },
      });
    });
  }

  // Hero booking card expand/collapse and form update
  const bookingCard = document.getElementById("booking-card");
  const expandBtn = document.getElementById("expand-booking");
  const collapseBtn = document.getElementById("collapse-booking");
  const heroBookCta = document.getElementById("hero-book-cta");
  const heroPrice = document.getElementById("hero-price");
  const heroService = document.getElementById("hero-service");
  const toggleCard = (state) => {
    if (!bookingCard) return;
    bookingCard.dataset.state = state;
  };
  expandBtn?.addEventListener("click", () => toggleCard("expanded"));
  collapseBtn?.addEventListener("click", () => toggleCard("compact"));
  heroBookCta?.addEventListener("click", (e) => {
    e.preventDefault();
    toggleCard("expanded");
    bookingCard?.scrollIntoView({ behavior: "smooth", block: "center" });
  });

  // Hero form price update
  heroService?.addEventListener("change", () => {
    const price = heroService.selectedOptions[0]?.dataset.price || heroService.value || "220";
    if (heroPrice) heroPrice.textContent = `${price} lei`;
  });

  const counterEl = document.getElementById("orders-counter");
  if (counterEl) {
    const target = parseInt(counterEl.dataset.target || "0", 10);
    let current = 0;
    const step = Math.max(1, Math.round(target / 60));
    const tick = () => {
      current = Math.min(target, current + step);
      counterEl.textContent = current.toLocaleString("ro-RO");
      if (current < target) requestAnimationFrame(tick);
    };
    tick();
  }

  // Order status demo
  const advanceBtn = document.getElementById("advance-order");
  const orderChip = document.getElementById("order-status-chip");
  const toast = document.getElementById("order-toast");
  const orderCard = document.getElementById("demo-order");
  const timelineDots = orderCard ? orderCard.querySelectorAll(".timeline-dot") : [];
  const states = [
    { label: "În așteptare", width: 25, color: "rgba(234,179,8,0.2)", text: "#854d0e" },
    { label: "Confirmată", width: 55, color: "rgba(34,197,94,0.25)", text: "#166534" },
    { label: "În curs", width: 80, color: "rgba(59,130,246,0.22)", text: "#1d4ed8" },
    { label: "Finalizată", width: 100, color: "rgba(16,185,129,0.3)", text: "#0f766e" },
  ];
  let stateIndex = 0;
  const toggleDetailsBtn = document.getElementById("toggle-order-details");
  toggleDetailsBtn?.addEventListener("click", () => orderCard?.classList.toggle("card-open"));
  advanceBtn?.addEventListener("click", () => {
    stateIndex = (stateIndex + 1) % states.length;
    const next = states[stateIndex];
    if (orderChip) {
      orderChip.textContent = next.label;
      orderChip.style.background = next.color;
      orderChip.style.color = next.text;
    }
    const bar = orderCard?.querySelector(".progress-bar");
    if (bar) bar.style.width = `${next.width}%`;
    orderCard?.classList.toggle("card-open", stateIndex >= 2);
    timelineDots.forEach((dot, idx) => dot.classList.toggle("active", idx <= stateIndex));
    if (toast) {
      toast.textContent = `Comanda ta este: ${next.label}!`;
      toast.classList.add("visible");
      setTimeout(() => toast.classList.remove("visible"), 1400);
    }
    if (stateIndex === states.length - 1) {
      fireConfetti(orderCard);
    }
  });

  // Page transition + loader
  const overlay = document.querySelector(".page-transition");
  const pageLoader = document.querySelector(".loader-overlay");
  const lottieLoader = document.getElementById("loader-lottie");
  if (window.lottie && lottieLoader) {
    lottie.loadAnimation({
      container: lottieLoader,
      renderer: "svg",
      loop: true,
      autoplay: true,
      path: "https://assets4.lottiefiles.com/packages/lf20_usmfx6bp.json",
    });
  }
  window.addEventListener("beforeunload", () => {
    overlay?.classList.add("active");
  });
  window.addEventListener("load", () => {
    overlay?.classList.remove("active");
  });

  document.querySelectorAll("[data-loader-target]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const target = document.querySelector(btn.dataset.loaderTarget);
      target?.classList.add("active");
      setTimeout(() => target?.classList.remove("active"), 1500);
    });
  });

  // Optional Lottie for empty services
  if (window.lottie) {
    const empty = document.getElementById("services-empty-lottie");
    if (empty) {
      lottie.loadAnimation({
        container: empty,
        renderer: "svg",
        loop: true,
        autoplay: true,
        path: "https://assets6.lottiefiles.com/packages/lf20_j2ka3n4z.json",
      });
    }

    // Booking cards reveal
    const bookingCards = document.querySelectorAll(".booking-card");
    if (bookingCards.length) {
      gsap.from(bookingCards, {
        scrollTrigger: {
          trigger: bookingCards[0].closest(".section") || bookingCards[0],
          start: "top 85%",
        },
        y: 26,
        opacity: 0,
        stagger: 0.08,
        duration: 0.55,
        ease: "power2.out",
      });
    }

    // Booking timeline items
    const timelineItems = document.querySelectorAll(".booking-timeline__item");
    if (timelineItems.length) {
      gsap.from(timelineItems, {
        scrollTrigger: {
          trigger: timelineItems[0].closest(".section") || timelineItems[0],
          start: "top 85%",
        },
        x: -12,
        opacity: 0,
        stagger: 0.1,
        duration: 0.5,
        ease: "power2.out",
      });
    }
  }

  // FAQ accordion with persistence
  document.querySelectorAll(".accordion-item").forEach((item) => {
    const trigger = item.querySelector(".accordion-trigger");
    const key = "faq-open";
    const stored = localStorage.getItem(key);
    if (stored && trigger && trigger.textContent === stored) {
      item.classList.add("open");
    }
    trigger?.addEventListener("click", () => {
      const isOpen = item.classList.contains("open");
      document.querySelectorAll(".accordion-item").forEach((el) => el.classList.remove("open"));
      if (!isOpen) {
        item.classList.add("open");
        localStorage.setItem(key, trigger.textContent || "");
      } else {
        localStorage.removeItem(key);
      }
    });
  });

  // Modal open/close
  document.querySelectorAll("[data-open-modal]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const modal = document.querySelector(btn.dataset.openModal);
      modal?.classList.add("open");
    });
  });
  document.querySelectorAll("[data-close-modal]").forEach((btn) => {
    btn.addEventListener("click", () => {
      btn.closest(".modal")?.classList.remove("open");
    });
  });

  // Skeleton groups
  document.querySelectorAll("[data-skeleton]").forEach((group) => {
    group.classList.add("loading");
    setTimeout(() => group.classList.remove("loading"), 600);
  });

  // Fetch live reviews
  const reviewsGrid = document.getElementById("reviews-grid");
  if (reviewsGrid) {
    const renderReviews = (items) => {
      reviewsGrid.innerHTML = "";
      items.forEach((rev) => {
        const card = document.createElement("div");
        card.className = "card glass hover-up";
        card.innerHTML = `
          <div class="badge">⭐ ${rev.rating || "4.8"}</div>
          <h3>${rev.author || "Client"}</h3>
          <p>${rev.text || ""}</p>
          <div class="muted">${rev.service || ""}</div>
        `;
        reviewsGrid.appendChild(card);
      });
    };
    fetch("/api/reviews/?page_size=6")
      .then((res) => res.json())
      .then((data) => {
        const results = data.results || [];
        const mapped = results.map((r) => ({
          author: r.user_name || "Client",
          rating: r.rating,
          text: r.comment || r.text || "",
          service: r.service?.name || "",
        }));
        renderReviews(mapped);
      })
      .catch(() => {
        renderReviews([
          { author: "Ana", rating: 5, text: "Rapid și politicos, problema rezolvată în 30 min.", service: "Instalații" },
          { author: "Mihai", rating: 4.9, text: "Electrician punctal, a explicat clar soluția.", service: "Electrică" },
          { author: "Ioana", rating: 4.8, text: "Curățenie impecabilă, recomand.", service: "Curățenie" },
        ]);
      });
  }

  // Confetti helper
  function fireConfetti(target) {
    if (!target) return;
    const colors = ["#2ab3b8", "#f6a721", "#23a0a6", "#0ea5e9"];
    for (let i = 0; i < 20; i++) {
      const piece = document.createElement("span");
      piece.className = "confetti";
      piece.style.background = colors[i % colors.length];
      piece.style.left = `${50 + Math.random() * 30 - 15}%`;
      piece.style.animationDelay = `${Math.random() * 0.3}s`;
      target.appendChild(piece);
      setTimeout(() => piece.remove(), 1200);
    }
  }
});
