interface HeroProps {
  onStartJourney: () => void
}

export default function Hero({ onStartJourney }: HeroProps) {
  return (
    <div className="relative min-h-screen flex items-center justify-center px-4 sm:px-6 lg:px-8">
      {/* Floating elements */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/4 w-2 h-2 bg-blue-400 rounded-full animate-float-slow" />
        <div className="absolute top-1/3 right-1/3 w-3 h-3 bg-purple-400 rounded-full animate-float-medium" />
        <div className="absolute bottom-1/4 left-1/3 w-2 h-2 bg-cyan-400 rounded-full animate-float-fast" />
        <div className="absolute top-2/3 right-1/4 w-4 h-4 bg-pink-400 rounded-full animate-float-slow" />
      </div>

      <div className="relative max-w-5xl mx-auto text-center">
        {/* Main heading */}
        <div className="mb-8 animate-fade-in">
          <div className="inline-block mb-6">
            <div className="relative">
              <div className="absolute inset-0 bg-gradient-to-r from-blue-500 via-purple-500 to-pink-500 rounded-full blur-2xl opacity-50 animate-pulse-glow" />
              <div className="relative text-9xl animate-bounce-slow">
                🗺️
              </div>
            </div>
          </div>
          
          <h1 className="text-6xl sm:text-7xl md:text-8xl lg:text-9xl font-black mb-6">
            <span className="inline-block bg-gradient-to-r from-blue-400 via-cyan-400 to-purple-400 bg-clip-text text-transparent animate-gradient pb-2">
              Прогулка
            </span>
            <br />
            <span className="inline-block bg-gradient-to-r from-purple-400 via-pink-400 to-red-400 bg-clip-text text-transparent animate-gradient-reverse pb-2">
              мечты
            </span>
          </h1>
          
          <p className="text-xl sm:text-2xl md:text-3xl text-blue-300/90 font-light max-w-3xl mx-auto leading-relaxed animate-fade-in-up" style={{ animationDelay: '0.2s' }}>
            Искусственный интеллект создаст <span className="text-cyan-400 font-semibold">персональный маршрут</span> по Нижнему Новгороду специально для вас
          </p>
        </div>

        {/* Features grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-12 animate-fade-in-up" style={{ animationDelay: '0.4s' }}>
          {[
            { emoji: '🎯', title: 'Персонально', desc: 'Учитываем ваши интересы' },
            { emoji: '☕', title: 'Умные перерывы', desc: 'Кафе в нужный момент' },
            { emoji: '🚶', title: 'Реальные пути', desc: 'Настоящие улицы' },
            { emoji: '✨', title: 'AI-подсказки', desc: 'Живые объяснения' }
          ].map((feature, i) => (
            <div
              key={i}
              className="group relative p-6 rounded-3xl backdrop-blur-xl bg-white/5 border border-white/10 hover:border-white/30 transition-all hover:scale-105 hover:-translate-y-2 cursor-default"
              style={{ animationDelay: `${0.5 + i * 0.1}s` }}
            >
              <div className="absolute inset-0 bg-gradient-to-br from-blue-500/10 to-purple-500/10 rounded-3xl opacity-0 group-hover:opacity-100 transition-opacity" />
              <div className="relative">
                <div className="text-5xl mb-3 transform group-hover:scale-110 transition-transform">
                  {feature.emoji}
                </div>
                <h3 className="text-lg font-bold text-white mb-1">
                  {feature.title}
                </h3>
                <p className="text-sm text-blue-300/70">
                  {feature.desc}
                </p>
              </div>
            </div>
          ))}
        </div>

        {/* CTA Button */}
        <div className="animate-fade-in-up" style={{ animationDelay: '0.8s' }}>
          <button
            onClick={onStartJourney}
            className="group relative px-12 py-6 text-2xl font-black text-white overflow-hidden rounded-full transition-all hover:scale-110 hover:shadow-2xl hover:shadow-blue-500/50"
          >
            <div className="absolute inset-0 bg-gradient-to-r from-blue-600 via-purple-600 to-pink-600 transition-transform group-hover:scale-110" />
            <div className="absolute inset-0 bg-gradient-to-r from-cyan-600 via-blue-600 to-purple-600 opacity-0 group-hover:opacity-100 transition-opacity animate-gradient" />
            <span className="relative flex items-center gap-4">
              Начать путешествие
              <span className="text-4xl transform group-hover:translate-x-2 transition-transform">
                →
              </span>
            </span>
          </button>
          
          <p className="mt-6 text-blue-300/50 text-sm animate-pulse">
            Бесплатно • Без регистрации • За 30 секунд
          </p>
        </div>

        {/* Scroll indicator */}
        <div className="absolute bottom-12 left-1/2 -translate-x-1/2 animate-bounce-slow">
          <div className="w-8 h-12 rounded-full border-2 border-white/30 flex items-start justify-center p-2">
            <div className="w-1 h-3 bg-white/50 rounded-full animate-scroll" />
          </div>
        </div>
      </div>
    </div>
  )
}