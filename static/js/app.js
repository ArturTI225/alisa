document.addEventListener("DOMContentLoaded", () => {
  // Mobile sidebar toggle for platform shell.
  const sidebar = document.getElementById("shell-sidebar");
  const openSidebarButtons = document.querySelectorAll("[data-open-sidebar]");

  const closeSidebar = () => {
    document.body.classList.remove("sidebar-open");
  };

  openSidebarButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      document.body.classList.toggle("sidebar-open");
    });
  });

  sidebar?.addEventListener("click", (event) => {
    if (event.target === sidebar) closeSidebar();
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeSidebar();
  });

  window.addEventListener("resize", () => {
    if (window.innerWidth > 960) closeSidebar();
  });

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

  const focusableSelector = [
    'a[href]',
    'button:not([disabled])',
    'input:not([disabled]):not([type="hidden"])',
    'select:not([disabled])',
    'textarea:not([disabled])',
    'summary',
    '[tabindex]:not([tabindex="-1"])',
  ].join(",");

  const getFocusable = (container) =>
    Array.from(container.querySelectorAll(focusableSelector)).filter(
      (node) => !node.hasAttribute("hidden") && !node.closest("[hidden]")
    );

  const closeModal = (modal) => {
    if (!modal) return;
    modal.classList.remove("open");
    modal.setAttribute("aria-hidden", "true");
    const returnFocus = modal._returnFocus;
    if (returnFocus && typeof returnFocus.focus === "function") {
      returnFocus.focus();
    }
  };

  const openModal = (modal, preferredFocus) => {
    if (!modal) return;
    modal._returnFocus = document.activeElement;
    modal.classList.add("open");
    modal.setAttribute("aria-hidden", "false");
    const target = preferredFocus || getFocusable(modal)[0];
    if (target && typeof target.focus === "function") {
      requestAnimationFrame(() => target.focus());
    }
  };

  // Pending submit state for mutation forms.
  document.querySelectorAll("form").forEach((form) => {
    form.addEventListener("submit", (event) => {
      const submitter = event.submitter;
      const button = submitter?.matches("button[type='submit'][data-pending-label]")
        ? submitter
        : form.querySelector("button[type='submit'][data-pending-label]");

      if (!button || button.disabled) return;

      if (!button.dataset.originalLabel) {
        button.dataset.originalLabel = button.textContent.trim();
      }

      button.textContent = button.dataset.pendingLabel;
      button.disabled = true;
      button.setAttribute("aria-disabled", "true");
      form.setAttribute("aria-busy", "true");
    });
  });

  // Live notifications: popup + sound
  const isAuthenticated = !!document.querySelector(".nav-user");
  const soundEnabled = document.body.dataset.notificationSoundEnabled === "true";
  let seenNotifIds = new Set();
  let notifsBootstrapped = false;
  let audioUnlocked = false;
  let audioCtx = null;

  const unlockAudio = () => {
    audioUnlocked = true;
    const Ctx = window.AudioContext || window.webkitAudioContext;
    if (Ctx && !audioCtx) {
      try {
        audioCtx = new Ctx();
      } catch (e) {
        // Ignore audio init failures; visual popup still works.
      }
    }
  };

  if (soundEnabled) {
    window.addEventListener("pointerdown", unlockAudio, { once: true });
    window.addEventListener("keydown", unlockAudio, { once: true });
  }

  const playNotificationSound = () => {
    if (!soundEnabled || !audioUnlocked || !audioCtx) return;
    try {
      const now = audioCtx.currentTime;
      const gain = audioCtx.createGain();
      gain.gain.setValueAtTime(0.001, now);
      gain.gain.exponentialRampToValueAtTime(0.08, now + 0.01);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.25);
      gain.connect(audioCtx.destination);

      const osc = audioCtx.createOscillator();
      osc.type = "sine";
      osc.frequency.setValueAtTime(920, now);
      osc.frequency.setValueAtTime(1220, now + 0.11);
      osc.connect(gain);
      osc.start(now);
      osc.stop(now + 0.26);
    } catch (e) {
      // Ignore sound errors to avoid breaking page scripts.
    }
  };

  const ensureNotifStack = () => {
    let stack = document.getElementById("notif-live-stack");
    if (stack) return stack;
    stack = document.createElement("div");
    stack.id = "notif-live-stack";
    stack.className = "notif-live-stack";
    document.body.appendChild(stack);
    return stack;
  };

  const showNotificationPopup = (notif) => {
    const stack = ensureNotifStack();
    const popup = document.createElement("div");
    popup.className = "notif-live-popup";
    popup.setAttribute("role", "status");

    const title = document.createElement("strong");
    title.textContent = notif.title || "Notificare noua";
    popup.appendChild(title);

    const body = document.createElement("p");
    body.textContent = notif.body || "";
    popup.appendChild(body);

    const closeBtn = document.createElement("button");
    closeBtn.type = "button";
    closeBtn.className = "notif-live-close";
    closeBtn.setAttribute("aria-label", "Inchide");
    closeBtn.textContent = "×";
    popup.appendChild(closeBtn);

    if (notif.link) {
      popup.classList.add("clickable");
      popup.addEventListener("click", (event) => {
        const closeBtn = event.target.closest(".notif-live-close");
        if (closeBtn) return;
        window.location.href = notif.link;
      });
    }

    const closePopup = () => {
      popup.classList.add("hide");
      setTimeout(() => popup.remove(), 200);
    };

    closeBtn.addEventListener("click", (event) => {
      event.stopPropagation();
      closePopup();
    });

    stack.prepend(popup);
    setTimeout(() => popup.classList.add("show"), 10);
    setTimeout(closePopup, 5200);
  };

  const normalizeNotifications = (payload) => {
    if (Array.isArray(payload)) return payload;
    if (payload && Array.isArray(payload.results)) return payload.results;
    return [];
  };

  const rememberNotifId = (id) => {
    seenNotifIds.add(id);
    if (seenNotifIds.size <= 300) return;
    const trimmed = Array.from(seenNotifIds).slice(-200);
    seenNotifIds = new Set(trimmed);
  };

  const fetchNotifsLive = async () => {
    if (!isAuthenticated) return;
    try {
      const res = await fetch("/api/notifications/");
      if (!res.ok) return;
      const items = normalizeNotifications(await res.json());
      const unreadItems = items.filter((n) => !n.is_read);

      if (!notifsBootstrapped) {
        unreadItems.forEach((n) => rememberNotifId(n.id));
        notifsBootstrapped = true;
        return;
      }

      const freshUnread = unreadItems.filter((n) => !seenNotifIds.has(n.id));
      if (!freshUnread.length) return;

      freshUnread
        .sort((a, b) => (a.id || 0) - (b.id || 0))
        .forEach((n) => {
          rememberNotifId(n.id);
          showNotificationPopup(n);
        });

      playNotificationSound();
    } catch (e) {
      console.warn("Notif live fetch failed", e);
    }
  };

  if (isAuthenticated) {
    fetchNotifsLive();
    setInterval(fetchNotifsLive, 12000);
  }

  // User menu keyboard navigation
  const accountMenus = Array.from(document.querySelectorAll("[data-menu]"));
  const closeMenus = (exceptMenu = null) => {
    accountMenus.forEach((menu) => {
      if (menu !== exceptMenu) menu.open = false;
    });
  };

  accountMenus.forEach((menu) => {
    const trigger = menu.querySelector("[data-menu-trigger]");
    const items = () => Array.from(menu.querySelectorAll("[data-menu-item]"));
    const syncExpanded = () => {
      trigger?.setAttribute("aria-expanded", menu.open ? "true" : "false");
    };

    syncExpanded();
    menu.addEventListener("toggle", () => {
      if (menu.open) closeMenus(menu);
      syncExpanded();
    });

    trigger?.addEventListener("keydown", (event) => {
      if (event.key === "ArrowDown") {
        event.preventDefault();
        menu.open = true;
        requestAnimationFrame(() => items()[0]?.focus());
      }
    });

    menu.addEventListener("keydown", (event) => {
      if (!menu.open) return;
      const menuItems = items();
      if (!menuItems.length) return;

      const currentIndex = menuItems.indexOf(document.activeElement);
      if (event.key === "Escape") {
        event.preventDefault();
        menu.open = false;
        trigger?.focus();
        return;
      }

      if (event.key === "ArrowDown") {
        event.preventDefault();
        const nextIndex = currentIndex < 0 ? 0 : (currentIndex + 1) % menuItems.length;
        menuItems[nextIndex]?.focus();
      }

      if (event.key === "ArrowUp") {
        event.preventDefault();
        const nextIndex = currentIndex <= 0 ? menuItems.length - 1 : currentIndex - 1;
        menuItems[nextIndex]?.focus();
      }

      if (event.key === "Home") {
        event.preventDefault();
        menuItems[0]?.focus();
      }

      if (event.key === "End") {
        event.preventDefault();
        menuItems[menuItems.length - 1]?.focus();
      }
    });
  });

  document.addEventListener("click", (event) => {
    accountMenus.forEach((menu) => {
      if (menu.open && !menu.contains(event.target)) {
        menu.open = false;
      }
    });
  });

  // Command palette
  const commandPalette = document.getElementById("command-palette");
  const commandInput = commandPalette?.querySelector("[data-command-input]");
  const commandEmpty = commandPalette?.querySelector("[data-command-empty]");
  const commandItems = commandPalette
    ? Array.from(commandPalette.querySelectorAll("[data-command-item]"))
    : [];

  const getVisibleCommandItems = () => commandItems.filter((item) => !item.hidden);

  const filterCommandItems = () => {
    if (!commandInput) return;
    const term = commandInput.value.toLowerCase().trim();
    let visibleCount = 0;
    commandItems.forEach((item) => {
      const haystack = (item.dataset.commandLabel || item.textContent || "").toLowerCase();
      const matches = !term || haystack.includes(term);
      item.hidden = !matches;
      if (matches) visibleCount += 1;
    });
    if (commandEmpty) commandEmpty.hidden = visibleCount > 0;
  };

  const openCommandPalette = () => {
    if (!commandPalette) return;
    if (commandInput) {
      commandInput.value = "";
      filterCommandItems();
    }
    openModal(commandPalette, commandInput);
  };

  const moveCommandFocus = (direction) => {
    const visibleItems = getVisibleCommandItems();
    if (!visibleItems.length) return;
    const currentIndex = visibleItems.indexOf(document.activeElement);
    const nextIndex =
      currentIndex < 0
        ? 0
        : (currentIndex + direction + visibleItems.length) % visibleItems.length;
    visibleItems[nextIndex]?.focus();
  };

  document.querySelectorAll("[data-open-command-palette]").forEach((button) => {
    button.addEventListener("click", () => openCommandPalette());
  });

  commandInput?.addEventListener("input", filterCommandItems);
  commandInput?.addEventListener("keydown", (event) => {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      moveCommandFocus(1);
      return;
    }

    if (event.key === "Enter") {
      const firstVisible = getVisibleCommandItems()[0];
      if (firstVisible) {
        event.preventDefault();
        firstVisible.click();
      }
    }
  });

  commandItems.forEach((item) => {
    item.addEventListener("keydown", (event) => {
      if (event.key === "ArrowDown") {
        event.preventDefault();
        moveCommandFocus(1);
      }

      if (event.key === "ArrowUp") {
        event.preventDefault();
        if (document.activeElement === getVisibleCommandItems()[0] && commandInput) {
          commandInput.focus();
        } else {
          moveCommandFocus(-1);
        }
      }

      if (event.key === "Home") {
        event.preventDefault();
        getVisibleCommandItems()[0]?.focus();
      }

      if (event.key === "End") {
        event.preventDefault();
        const visibleItems = getVisibleCommandItems();
        visibleItems[visibleItems.length - 1]?.focus();
      }
    });
  });

  document.addEventListener("keydown", (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
      event.preventDefault();
      if (commandPalette?.classList.contains("open")) {
        closeModal(commandPalette);
      } else {
        openCommandPalette();
      }
      return;
    }

    if (event.key === "Escape") {
      const openModalEl = document.querySelector(".modal.open");
      if (openModalEl) {
        event.preventDefault();
        closeModal(openModalEl);
        return;
      }

      const openMenu = accountMenus.find((menu) => menu.open);
      if (openMenu) {
        event.preventDefault();
        openMenu.open = false;
        openMenu.querySelector("[data-menu-trigger]")?.focus();
      }
    }
  });

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
    if (bookingCards.length && window.gsap && window.ScrollTrigger) {
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
    if (timelineItems.length && window.gsap && window.ScrollTrigger) {
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
      openModal(modal);
    });
  });
  document.querySelectorAll("[data-close-modal]").forEach((btn) => {
    btn.addEventListener("click", () => {
      closeModal(btn.closest(".modal"));
    });
  });
  document.querySelectorAll(".modal").forEach((modal) => {
    modal.addEventListener("click", (event) => {
      if (event.target === modal) {
        closeModal(modal);
      }
    });
    modal.addEventListener("keydown", (event) => {
      if (event.key !== "Tab") return;
      const focusable = getFocusable(modal);
      if (!focusable.length) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    });
  });

  // Chat keyboard support
  document.querySelectorAll(".chat-composer textarea").forEach((textarea) => {
    textarea.addEventListener("keydown", (event) => {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        textarea.form?.requestSubmit();
      }
    });
  });

  // Skeleton groups
  document.querySelectorAll("[data-skeleton]").forEach((group) => {
    if (!group.children.length) return;
    const duration = parseInt(group.dataset.skeletonDuration || "550", 10);
    group.classList.add("loading");
    group.setAttribute("aria-busy", "true");
    setTimeout(() => {
      group.classList.remove("loading");
      group.setAttribute("aria-busy", "false");
    }, duration);
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
