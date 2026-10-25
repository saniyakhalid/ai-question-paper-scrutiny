import React, { useEffect, useState } from 'react';
import { ChevronLeft, ChevronRight, Pause, Play } from 'lucide-react';

export default function ImageSlider({ slides = [], intervalMs = 2000, className = '' }) {
  const [index, setIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(true);

  useEffect(() => {
    if (slides.length <= 1 || !isPlaying) return undefined;

    const timer = setInterval(() => {
      setIndex((prev) => (prev + 1) % slides.length);
    }, intervalMs);

    return () => clearInterval(timer);
  }, [slides.length, intervalMs, isPlaying]);

  if (!slides.length) return null;

  const go = (dir) => {
    setIndex((prev) => (prev + dir + slides.length) % slides.length);
  };

  return (
    <div
      className={`relative overflow-hidden rounded-2xl bg-slate-900 border border-slate-200/80 shadow-xl group ${className}`}
      role="region"
      aria-label="ADCET campus photographs"
      aria-roledescription="carousel"
    >
      {/* Slides Container */}
      <div className="relative w-full h-[clamp(14rem,55vw,32rem)] sm:h-[clamp(20rem,38vw,32rem)]">
        {slides.map((slide, i) => {
          const isActive = i === index;
          return (
            <div
              key={i}
                className={`absolute inset-0 transition-opacity duration-700 ease-in-out ${
                isActive ? 'opacity-100 z-10 scale-100' : 'opacity-0 z-0 pointer-events-none scale-105'
                } transition-transform duration-700`}
            >
              <img
                src={slide.src}
                alt={slide.alt || `ADCET Campus Image ${i + 1}`}
                className="w-full h-full object-cover object-center"
                loading="eager"
                draggable="false"
              />

              {/* Sophisticated dual gradient overlay that keeps light college tone & readable captions */}
              <div className="absolute inset-0 bg-gradient-to-t from-adcet-navy/90 via-adcet-navy/30 to-black/20" />

              {/* Slide Content Overlay */}
              <div className="absolute bottom-0 left-0 right-0 p-6 sm:p-10 text-white z-20">
                <div className="max-w-4xl space-y-2">
                  {slide.badge && (
                    <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-adcet-red text-white text-[11px] font-bold uppercase tracking-wider shadow-md">
                      {slide.badge}
                    </span>
                  )}
                  {slide.title && (
                    <h2 className="text-xl sm:text-3xl md:text-4xl font-display font-black tracking-tight drop-shadow-md text-white">
                      {slide.title}
                    </h2>
                  )}
                  {slide.subtitle && (
                    <p className="text-xs sm:text-sm md:text-base text-white/90 max-w-2xl font-normal leading-relaxed drop-shadow">
                      {slide.subtitle}
                    </p>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Navigation Arrows */}
      {slides.length > 1 && (
        <>
          <button
            type="button"
            onClick={() => go(-1)}
            className="absolute left-3 sm:left-5 top-1/2 -translate-y-1/2 z-30 p-2.5 rounded-full bg-white/90 text-adcet-navy shadow-lg hover:bg-white hover:scale-110 active:scale-95 transition-all focus:outline-none"
            aria-label="Previous campus slide"
          >
            <ChevronLeft className="w-5 h-5 text-adcet-navy" />
          </button>

          <button
            type="button"
            onClick={() => go(1)}
            className="absolute right-3 sm:right-5 top-1/2 -translate-y-1/2 z-30 p-2.5 rounded-full bg-white/90 text-adcet-navy shadow-lg hover:bg-white hover:scale-110 active:scale-95 transition-all focus:outline-none"
            aria-label="Next campus slide"
          >
            <ChevronRight className="w-5 h-5 text-adcet-navy" />
          </button>

          {/* Bottom Indicators & Auto-scroll status */}
          <div className="absolute bottom-4 sm:bottom-6 right-6 sm:right-10 z-30 flex items-center gap-2">
            <button
              type="button"
              onClick={() => setIsPlaying(!isPlaying)}
              className="p-1.5 rounded-full bg-black/40 text-white/80 hover:text-white hover:bg-black/60 transition-colors mr-1"
              title={isPlaying ? "Pause auto-slide" : "Resume auto-slide"}
              aria-label={isPlaying ? 'Pause automatic campus slideshow' : 'Resume automatic campus slideshow'}
            >
              {isPlaying ? <Pause className="w-3 h-3" /> : <Play className="w-3 h-3" />}
            </button>

            {slides.map((_, i) => (
              <button
                key={i}
                type="button"
                onClick={() => setIndex(i)}
                className={`h-2 rounded-full transition-all duration-300 ${
                  i === index ? 'w-8 bg-adcet-red shadow-md' : 'w-2 bg-white/60 hover:bg-white'
                }`}
                aria-label={`Go to slide ${i + 1}`}
              />
            ))}
          </div>
        </>
      )}
    </div>
  );
}
