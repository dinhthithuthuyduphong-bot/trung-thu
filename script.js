/* =========================================================
   TRUNG THU CHO EM — FINAL ONE-PAGE VERSION
   Pastel two-door card + one-page thank-you popup
   ========================================================= */


/* =========================================================
   SETTINGS
   ========================================================= */

const RESUME_JOURNEY_MUSIC_ON_VIDEO_END = false;

/*
  Nhạc lời cảm ơn.
  Đang mặc định loop 1:11 -> 1:49.
  Nếu dùng bài khác, đổi 2 số này.
*/
const THANKYOU_MUSIC_START = 71;
const THANKYOU_MUSIC_END = 109;

const THANKYOU_VOLUME = 0.27;

/*
  Nhạc không lời của hành trình.
  File audio có loop nên không cần END.
*/
const JOURNEY_MUSIC_START = 0;
const JOURNEY_VOLUME = 0.18;

const MUSIC_FADE_DURATION = 900;

/*
  Auto scroll:
  18 px/s = chậm, chill.
  Chạm/click/wheel -> dừng.
  Đổi 0 để tắt.
*/
const AUTO_SCROLL_SPEED = 18;


/* =========================================================
   ELEMENTS
   ========================================================= */

const thankYouMusic =
  document.getElementById("thankYouMusic");

const journeyMusic =
  document.getElementById("journeyMusic");

const openCardBtn =
  document.getElementById("openCardBtn");

const cover =
  document.getElementById("cover");

const content =
  document.getElementById("cardContent");

const welcomePopup =
  document.getElementById("welcomePopup");

const closeWelcomePopup =
  document.getElementById("closeWelcomePopup");

const continueJourneyBtn =
  document.getElementById("continueJourneyBtn");

const journeyStart =
  document.getElementById("journey");

const musicToggle =
  document.getElementById("musicToggle");

const musicIcon =
  document.getElementById("musicIcon");

const journeyMenuBtn =
  document.getElementById("journeyMenuBtn");

const readThankYouAgainBtn =
  document.getElementById("readThankYouAgainBtn");

const youtubePlayers =
  new Map();


/* =========================================================
   STATE
   ========================================================= */

let journeyMusicUserMuted = false;
let journeyMusicWasPlayingBeforeVideo = false;

let autoScrollActive = false;
let autoScrollFrame = null;
let lastAutoScrollTime = 0;
let scrollAccumulator = 0;


/* =========================================================
   GENERIC AUDIO FADE
   ========================================================= */

function fadeAudio(
  audio,
  targetVolume,
  duration = MUSIC_FADE_DURATION,
  onDone = null
) {

  if (!audio) return;

  /*
    Kill the previous fade on the same audio.
  */
  if (audio._fadeFrame) {
    cancelAnimationFrame(
      audio._fadeFrame
    );
  }

  const startVolume =
    Number.isFinite(audio.volume)
      ? audio.volume
      : 0;

  const difference =
    targetVolume -
    startVolume;

  const startTime =
    performance.now();


  function step(now) {

    const progress =
      Math.min(
        1,
        (now - startTime) /
        duration
      );

    audio.volume =
      Math.max(
        0,
        Math.min(
          1,
          startVolume +
          difference *
          progress
        )
      );

    if (progress < 1) {

      audio._fadeFrame =
        requestAnimationFrame(
          step
        );

    }
    else {

      audio._fadeFrame =
        null;

      audio.volume =
        targetVolume;

      if (
        typeof onDone ===
        "function"
      ) {

        onDone();

      }

    }

  }


  audio._fadeFrame =
    requestAnimationFrame(
      step
    );
}


/* =========================================================
   THANK-YOU MUSIC
   ========================================================= */

thankYouMusic.volume = 0;


/*
  Start at the selected section.
*/
thankYouMusic.addEventListener(
  "loadedmetadata",
  () => {

    if (
      Number.isFinite(
        thankYouMusic.duration
      ) &&
      thankYouMusic.duration >
        THANKYOU_MUSIC_START
    ) {

      thankYouMusic.currentTime =
        THANKYOU_MUSIC_START;

    }

  }
);


/*
  Loop selected segment.
*/
function keepThankYouMusicInRange() {

  if (
    !thankYouMusic.paused &&
    Number.isFinite(
      thankYouMusic.duration
    ) &&
    thankYouMusic.currentTime >=
      Math.min(
        THANKYOU_MUSIC_END,
        thankYouMusic.duration
      )
  ) {

    thankYouMusic.currentTime =
      Math.min(
        THANKYOU_MUSIC_START,
        Math.max(
          0,
          thankYouMusic.duration - .2
        )
      );

  }

  requestAnimationFrame(
    keepThankYouMusicInRange
  );
}

keepThankYouMusicInRange();


async function unlockThankYouMusic() {

  try {

    thankYouMusic.volume = 0;

    if (
      Number.isFinite(
        thankYouMusic.duration
      ) &&
      thankYouMusic.duration >
        THANKYOU_MUSIC_START
    ) {

      thankYouMusic.currentTime =
        THANKYOU_MUSIC_START;

    }

    await thankYouMusic.play();

  }
  catch (error) {

    console.info(
      "Trình duyệt chưa cho phát nhạc cảm ơn.",
      error
    );

  }

}


async function playThankYouMusic({
  restart = false
} = {}) {

  /*
    Popup mở -> nhạc hành trình không chạy cùng.
  */
  if (!journeyMusic.paused) {

    fadeAudio(
      journeyMusic,
      0,
      500,
      () => {

        journeyMusic.pause();
        journeyMusic.volume =
          JOURNEY_VOLUME;

      }
    );

  }


  if (
    restart &&
    Number.isFinite(
      thankYouMusic.duration
    )
  ) {

    thankYouMusic.currentTime =
      Math.min(
        THANKYOU_MUSIC_START,
        Math.max(
          0,
          thankYouMusic.duration - .2
        )
      );

  }


  thankYouMusic.volume = 0;


  try {

    await thankYouMusic.play();

    fadeAudio(
      thankYouMusic,
      THANKYOU_VOLUME,
      900
    );

  }
  catch (error) {

    console.info(
      "Không thể phát nhạc cảm ơn.",
      error
    );

  }

}


/* =========================================================
   JOURNEY MUSIC
   ========================================================= */

journeyMusic.volume =
  JOURNEY_VOLUME;


async function playJourneyMusic({
  restart = false
} = {}) {

  if (
    journeyMusicUserMuted
  ) {

    updateMusicIcon();
    return;

  }


  if (restart) {

    journeyMusic.currentTime =
      JOURNEY_MUSIC_START;

  }


  journeyMusic.volume = 0;


  try {

    await journeyMusic.play();

    fadeAudio(
      journeyMusic,
      JOURNEY_VOLUME,
      1100
    );

  }
  catch (error) {

    console.info(
      "Không thể phát nhạc hành trình.",
      error
    );

  }


  updateMusicIcon();
}


function stopJourneyMusic({
  fade = true
} = {}) {

  if (
    journeyMusic.paused
  ) {

    updateMusicIcon();
    return;

  }


  if (!fade) {

    journeyMusic.pause();
    journeyMusic.volume =
      JOURNEY_VOLUME;

    updateMusicIcon();

    return;
  }


  fadeAudio(
    journeyMusic,
    0,
    650,
    () => {

      journeyMusic.pause();
      journeyMusic.volume =
        JOURNEY_VOLUME;

      updateMusicIcon();

    }
  );

}


function updateMusicIcon() {

  if (!musicIcon) return;

  const silent =
    journeyMusic.paused ||
    journeyMusicUserMuted ||
    journeyMusic.volume === 0;

  musicIcon.textContent =
    silent
      ? "🔇"
      : "🔊";
}


/* =========================================================
   OPEN CARD
   ========================================================= */

openCardBtn.addEventListener(
  "click",
  async () => {

    /*
      iPhone/Safari:
      play() happens inside the user's click.
      Volume stays 0 while the doors open.
    */
    await unlockThankYouMusic();


    cover.classList.add(
      "is-opening"
    );


    /*
      Let the opening animation be visible.
    */
    setTimeout(
      async () => {

        content.hidden =
          false;


        if (
          !welcomePopup.open
        ) {

          welcomePopup.showModal();

        }


        /*
          Music belongs to the thank-you popup.
        */
        await playThankYouMusic();


        /*
          Fade the opening card away behind the popup.
        */
        cover.animate(
          [
            {
              opacity:1
            },

            {
              opacity:0
            }
          ],
          {
            duration:380,
            easing:"ease-out",
            fill:"forwards"
          }
        )
        .finished
        .finally(
          () => {

            cover.style.display =
              "none";

          }
        );

      },
      1100
    );

  }
);


/* =========================================================
   ENTER JOURNEY
   ========================================================= */

function enterJourney() {

  /*
    THANK-YOU SONG OUT
  */
  fadeAudio(
    thankYouMusic,
    0,
    700,
    () => {

      thankYouMusic.pause();
      thankYouMusic.volume =
        THANKYOU_VOLUME;

    }
  );


  /*
    JOURNEY INSTRUMENTAL IN
    This call is still in the user's button-click flow.
  */
  journeyMusicUserMuted =
    false;

  playJourneyMusic({
    restart:true
  });


  /*
    Close popup nicely.
  */
  if (
    welcomePopup.open
  ) {

    const popupBook =
      welcomePopup.querySelector(
        ".popup-book"
      );


    if (popupBook) {

      const animation =
        popupBook.animate(
          [
            {
              opacity:1,
              transform:
                "translateY(0) scale(1)"
            },

            {
              opacity:0,
              transform:
                "translateY(12px) scale(.985)"
            }
          ],
          {
            duration:300,
            easing:"ease-in",
            fill:"forwards"
          }
        );


      animation
        .finished
        .finally(
          () => {

            if (
              welcomePopup.open
            ) {

              welcomePopup.close();

            }


            /*
              Important:
              cancel fill:forwards so
              popup can reopen later.
            */
            animation.cancel();


            showJourney();

          }
        );


      return;

    }


    welcomePopup.close();

  }


  showJourney();

}


function showJourney() {

  if (journeyStart) {

    journeyStart.scrollIntoView({
      behavior:"smooth",
      block:"start"
    });

  }


  setTimeout(
    () => {

      if (
        AUTO_SCROLL_SPEED >
        0
      ) {

        startChillAutoScroll();

      }

    },
    1300
  );

}


continueJourneyBtn
  ?.addEventListener(
    "click",
    enterJourney
  );


/*
  X also enters the memories.
*/
closeWelcomePopup
  ?.addEventListener(
    "click",
    enterJourney
  );


/* =========================================================
   READ THANK-YOU AGAIN
   ========================================================= */

async function reopenThankYou() {

  stopChillAutoScroll();


  /*
    Stop journey instrumental.
  */
  stopJourneyMusic({
    fade:true
  });


  /*
    Make sure prior popup animations
    cannot keep it invisible.
  */
  const popupBook =
    welcomePopup.querySelector(
      ".popup-book"
    );


  popupBook
    ?.getAnimations()
    .forEach(
      animation =>
        animation.cancel()
    );


  if (
    !welcomePopup.open
  ) {

    welcomePopup.showModal();

  }


  await playThankYouMusic({
    restart:true
  });

}


readThankYouAgainBtn
  ?.addEventListener(
    "click",
    async event => {

      event.preventDefault();

      await reopenThankYou();

    }
  );


/* =========================================================
   CHILL AUTO SCROLL
   ========================================================= */

function startChillAutoScroll() {

  stopChillAutoScroll();

  autoScrollActive =
    true;

  lastAutoScrollTime =
    performance.now();

  scrollAccumulator = 0;


  const scroller =
    document.scrollingElement ||
    document.documentElement;


  function autoScrollLoop(now) {

    if (
      !autoScrollActive
    ) {

      return;

    }


    const deltaTime =
      Math.min(
        now -
        lastAutoScrollTime,
        50
      );


    lastAutoScrollTime =
      now;


    scrollAccumulator +=
      AUTO_SCROLL_SPEED *
      (deltaTime / 1000);


    if (
      scrollAccumulator >= 1
    ) {

      const pixels =
        Math.floor(
          scrollAccumulator
        );


      scroller.scrollTop +=
        pixels;


      scrollAccumulator -=
        pixels;

    }


    if (
      scroller.scrollTop +
      window.innerHeight >=
      scroller.scrollHeight - 5
    ) {

      stopChillAutoScroll();

      return;

    }


    autoScrollFrame =
      requestAnimationFrame(
        autoScrollLoop
      );

  }


  autoScrollFrame =
    requestAnimationFrame(
      autoScrollLoop
    );

}


function stopChillAutoScroll() {

  autoScrollActive =
    false;


  if (
    autoScrollFrame !== null
  ) {

    cancelAnimationFrame(
      autoScrollFrame
    );

  }


  autoScrollFrame =
    null;

  lastAutoScrollTime =
    0;

  scrollAccumulator =
    0;

}


document.addEventListener(
  "pointerdown",
  () => {

    if (
      autoScrollActive
    ) {

      stopChillAutoScroll();

    }

  },
  {
    passive:true
  }
);


window.addEventListener(
  "wheel",
  () => {

    if (
      autoScrollActive
    ) {

      stopChillAutoScroll();

    }

  },
  {
    passive:true
  }
);


/* =========================================================
   JOURNEY MUSIC TOGGLE
   ========================================================= */

musicToggle
  ?.addEventListener(
    "click",
    async () => {

      if (
        journeyMusic.paused
      ) {

        journeyMusicUserMuted =
          false;

        await playJourneyMusic();

      }
      else {

        journeyMusicUserMuted =
          true;

        stopJourneyMusic({
          fade:false
        });

      }

      updateMusicIcon();

    }
  );


journeyMusic.addEventListener(
  "play",
  updateMusicIcon
);

journeyMusic.addEventListener(
  "pause",
  updateMusicIcon
);

journeyMusic.addEventListener(
  "volumechange",
  updateMusicIcon
);

updateMusicIcon();


/* =========================================================
   JOURNEY MENU
   ========================================================= */

journeyMenuBtn
  ?.addEventListener(
    "click",
    () => {

      stopChillAutoScroll();

      journeyStart
        ?.scrollIntoView({
          behavior:"smooth",
          block:"start"
        });

    }
  );


/* =========================================================
   REVEAL
   ========================================================= */

const observer =
  new IntersectionObserver(
    entries => {

      entries.forEach(
        entry => {

          if (
            entry.isIntersecting
          ) {

            entry.target
              .classList
              .add(
                "is-visible"
              );

            observer.unobserve(
              entry.target
            );

          }

        }
      );

    },
    {
      threshold:.12
    }
  );


document
  .querySelectorAll(
    ".reveal"
  )
  .forEach(
    element => {

      observer.observe(
        element
      );

    }
  );


/* =========================================================
   TIMELINE
   ========================================================= */

const yearChips =
  [
    ...document
      .querySelectorAll(
        ".year-chip"
      )
  ];


const yearDetails =
  [
    ...document
      .querySelectorAll(
        ".timeline-year"
      )
  ];


function openYear(targetId) {

  stopChillAutoScroll();


  const target =
    document.getElementById(
      targetId
    );


  if (!target) return;


  target.open =
    true;


  yearChips.forEach(
    chip => {

      chip.classList.toggle(
        "is-current",

        chip.dataset.yearTarget ===
          targetId
      );

    }
  );


  setTimeout(
    () => {

      target.scrollIntoView({
        behavior:"smooth",
        block:"start"
      });

    },
    60
  );

}


yearChips.forEach(
  chip => {

    chip.addEventListener(
      "click",
      () => {

        openYear(
          chip.dataset.yearTarget
        );

      }
    );

  }
);


yearDetails.forEach(
  detail => {

    detail.addEventListener(
      "toggle",
      () => {

        if (
          detail.open
        ) {

          yearChips.forEach(
            chip => {

              chip.classList.toggle(
                "is-current",

                chip.dataset.yearTarget ===
                  detail.id
              );

            }
          );

        }

      }
    );

  }
);


/* =========================================================
   HORIZONTAL GALLERY CAROUSEL
   ========================================================= */

document
  .querySelectorAll(
    ".year-gallery"
  )
  .forEach(
    gallery => {

      /*
        Avoid wrapping twice.
      */
      if (
        gallery.parentElement
          ?.classList
          .contains(
            "gallery-scroll-shell"
          )
      ) {

        return;

      }


      const shell =
        document.createElement(
          "div"
        );


      shell.className =
        "gallery-scroll-shell";


      gallery.parentNode
        .insertBefore(
          shell,
          gallery
        );


      shell.appendChild(
        gallery
      );


      const hint =
        document.createElement(
          "div"
        );


      hint.className =
        "gallery-swipe-hint";


      hint.innerHTML =
        '<span>Vuốt để xem thêm</span><span class="swipe-arrow" aria-hidden="true">→</span>';


      shell.insertBefore(
        hint,
        gallery
      );


      const nextButton =
        document.createElement(
          "button"
        );


      nextButton.type =
        "button";


      nextButton.className =
        "gallery-next";


      nextButton.setAttribute(
        "aria-label",
        "Xem ảnh tiếp theo"
      );


      nextButton.innerHTML =
        "→";


      shell.appendChild(
        nextButton
      );


      const updateCarouselUI =
        () => {

          const maxScroll =
            Math.max(
              0,
              gallery.scrollWidth -
              gallery.clientWidth
            );


          const atEnd =
            gallery.scrollLeft >=
            maxScroll - 8;


          nextButton
            .classList
            .toggle(
              "is-hidden",

              atEnd ||
              maxScroll < 10
            );


          if (
            gallery.scrollLeft >
            20
          ) {

            hint.classList.add(
              "is-hidden"
            );

          }

        };


      nextButton
        .addEventListener(
          "click",
          () => {

            stopChillAutoScroll();


            const firstCard =
              gallery.querySelector(
                ".gallery-card"
              );


            const amount =
              firstCard

                ? firstCard
                    .getBoundingClientRect()
                    .width + 14

                : gallery.clientWidth *
                  .78;


            gallery.scrollBy({
              left:amount,
              behavior:"smooth"
            });

          }
        );


      let isDragging =
        false;

      let dragStartX =
        0;

      let startScrollLeft =
        0;

      let draggedDistance =
        0;


      gallery.addEventListener(
        "pointerdown",
        event => {

          stopChillAutoScroll();


          if (
            event.pointerType ===
            "touch"
          ) {

            return;

          }


          isDragging =
            true;

          draggedDistance =
            0;

          dragStartX =
            event.clientX;

          startScrollLeft =
            gallery.scrollLeft;


          gallery
            .setPointerCapture
            ?.(
              event.pointerId
            );

        }
      );


      gallery.addEventListener(
        "pointermove",
        event => {

          if (
            !isDragging ||
            event.pointerType ===
              "touch"
          ) {

            return;

          }


          const dx =
            event.clientX -
            dragStartX;


          draggedDistance =
            Math.max(
              draggedDistance,
              Math.abs(dx)
            );


          gallery.scrollLeft =
            startScrollLeft -
            dx;

        }
      );


      const stopDragging =
        () => {

          isDragging =
            false;

        };


      gallery.addEventListener(
        "pointerup",
        stopDragging
      );

      gallery.addEventListener(
        "pointercancel",
        stopDragging
      );

      gallery.addEventListener(
        "pointerleave",
        stopDragging
      );


      gallery
        .querySelectorAll(
          ".gallery-card"
        )
        .forEach(
          card => {

            card.addEventListener(
              "click",
              event => {

                if (
                  draggedDistance >
                  8
                ) {

                  event.preventDefault();

                  event
                    .stopImmediatePropagation();

                }


                draggedDistance =
                  0;

              },
              true
            );

          }
        );


      gallery.addEventListener(
        "scroll",
        updateCarouselUI,
        {
          passive:true
        }
      );


      window.addEventListener(
        "resize",
        updateCarouselUI
      );


      requestAnimationFrame(
        updateCarouselUI
      );

    }
  );


/* =========================================================
   IMAGE LIGHTBOX
   ========================================================= */

const lightbox =
  document.getElementById(
    "lightbox"
  );

const lightboxImage =
  document.getElementById(
    "lightboxImage"
  );

const closeLightbox =
  document.getElementById(
    "closeLightbox"
  );


document
  .querySelectorAll(
    ".gallery-card"
  )
  .forEach(
    card => {

      card.addEventListener(
        "click",
        () => {

          stopChillAutoScroll();


          lightboxImage.src =
            card.dataset.full;


          lightbox.showModal();

        }
      );

    }
  );


closeLightbox
  ?.addEventListener(
    "click",
    () => {

      lightbox.close();

    }
  );


lightbox
  ?.addEventListener(
    "click",
    event => {

      if (
        event.target ===
        lightbox
      ) {

        lightbox.close();

      }

    }
  );


/* =========================================================
   STATEMENT PLACEHOLDERS
   ========================================================= */

const resourceDialog =
  document.getElementById(
    "resourceDialog"
  );

const resourceDialogTitle =
  document.getElementById(
    "resourceDialogTitle"
  );

const resourceDialogText =
  document.getElementById(
    "resourceDialogText"
  );

const closeResourceDialog =
  document.getElementById(
    "closeResourceDialog"
  );


document
  .querySelectorAll(
    ".resource-placeholder[data-placeholder='true']"
  )
  .forEach(
    link => {

      link.addEventListener(
        "click",
        event => {

          stopChillAutoScroll();

          event.preventDefault();


          const year =
            link.dataset
                .resourceYear ||
            "";


          resourceDialogTitle
            .textContent =
              `Sao kê ${year} chưa được cập nhật`;


          resourceDialogText
            .textContent =
              "Sau khi có file PDF hoặc link Google Drive, chỉ cần gắn vào nút này. Giao diện không cần làm lại.";


          resourceDialog
            .showModal();

        }
      );

    }
  );


closeResourceDialog
  ?.addEventListener(
    "click",
    () => {

      resourceDialog.close();

    }
  );


resourceDialog
  ?.addEventListener(
    "click",
    event => {

      if (
        event.target ===
        resourceDialog
      ) {

        resourceDialog.close();

      }

    }
  );


/* =========================================================
   YOUTUBE
   ========================================================= */

window.onYouTubeIframeAPIReady =
  function () {

    document
      .querySelectorAll(
        ".timeline-youtube-player"
      )
      .forEach(
        (
          node,
          index
        ) => {

          const videoId =
            (
              node.dataset
                  .youtubeId ||
              ""
            )
            .trim();


          if (!videoId) return;


          const playerId =
            `timeline-player-${index}`;


          node.id =
            playerId;


          const shell =
            node.closest(
              ".timeline-video-shell"
            );


          shell
            ?.classList
            .remove(
              "is-empty"
            );


          const player =
            new YT.Player(
              playerId,
              {

                videoId,

                playerVars:{
                  start:
                    Number(
                      node.dataset
                          .start ||
                      0
                    ),
                  rel:0,
                  modestbranding:1,
                  playsinline:1
                },

                events:{
                  onStateChange:
                    event =>
                      onTimelinePlayerStateChange(
                        event,
                        shell
                      )
                }

              }
            );


          youtubePlayers.set(
            playerId,
            player
          );

        }
      );

  };


function onTimelinePlayerStateChange(
  event,
  shell
) {

  if (!window.YT) return;


  const endOverlay =
    shell
      ?.querySelector(
        ".timeline-video-end"
      );


  if (
    event.data ===
    YT.PlayerState.PLAYING
  ) {

    stopChillAutoScroll();


    if (endOverlay) {

      endOverlay.hidden =
        true;

    }


    journeyMusicWasPlayingBeforeVideo =
      !journeyMusic.paused &&
      !journeyMusicUserMuted;


    stopJourneyMusic({
      fade:true
    });

  }


  if (
    event.data ===
    YT.PlayerState.PAUSED
  ) {

    if (
      journeyMusicWasPlayingBeforeVideo &&
      !journeyMusicUserMuted
    ) {

      playJourneyMusic();

    }

  }


  if (
    event.data ===
    YT.PlayerState.ENDED
  ) {

    stopJourneyMusic({
      fade:false
    });


    if (
      RESUME_JOURNEY_MUSIC_ON_VIDEO_END &&
      !journeyMusicUserMuted
    ) {

      playJourneyMusic();

    }
    else if (
      endOverlay
    ) {

      endOverlay.hidden =
        false;

    }

  }

}


/*
  Existing "return to card/music" buttons.
*/
document
  .querySelectorAll(
    ".resume-card-music"
  )
  .forEach(
    button => {

      button.addEventListener(
        "click",
        async () => {

          const shell =
            button.closest(
              ".timeline-video-shell"
            );


          const overlay =
            shell
              ?.querySelector(
                ".timeline-video-end"
              );


          if (overlay) {

            overlay.hidden =
              true;

          }


          journeyMusicUserMuted =
            false;


          await playJourneyMusic();


          const year =
            button.closest(
              ".timeline-year"
            );


          year
            ?.scrollIntoView({
              behavior:"smooth",
              block:"start"
            });

        }
      );

    }
  );

