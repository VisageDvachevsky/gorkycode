interface HeroProps {
  onStartJourney: () => void
}

export default function Hero({ onStartJourney }: HeroProps) {
  return (
    <div className="relative min-h-screen flex items-center justify-center px-4 sm:px-6 lg:px-8">
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
            <span className="inline-block bg-gradient-to-r from-purple-400 via-pink-400 to-red-400 bg-clip-text text-transparent animate-gradient pb-2">
              твоей мечты
            </span>
          </h1>
          
          <p className="text-2xl sm:text-3xl text-blue-200/80 max-w-3xl mx-auto leading-relaxed">
            AI создаст персональный маршрут по Нижнему Новгороду специально для тебя
          </p>
        </div>

        {/* Feature highlights */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-12 animate-fade-in-up" style={{ animationDelay: '0.3s' }}>
          {[
            { icon: '🎯', title: 'Персонально', desc: 'Под твои интересы' },
            { icon: '⚡', title: 'Быстро', desc: 'За 30 секунд' },
            { icon: '☕', title: 'С кофе', desc: 'Кафе по пути' },
            { icon: '🤖', title: 'С AI', desc: 'Умные объяснения' }
          ].map((feature, index) => (
            <div
              key={feature.title}
              className="group relative animate-fade-in-up"
              style={{ animationDelay: `${0.4 + index * 0.1}s` }}
            >
              <div className="absolute -inset-0.5 bg-gradient-to-r from-blue-600 to-purple-600 rounded-2xl opacity-20 group-hover:opacity-40 blur transition-all" />
              <div className="relative backdrop-blur-2xl bg-white/10 border border-white/20 rounded-2xl p-6 hover:border-white/40 transition-all">
                <div className="text-5xl mb-3 transform group-hover:scale-110 transition-transform">
                  {feature.icon}
                </div>
                <h3 className="text-xl font-black text-white mb-1">
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