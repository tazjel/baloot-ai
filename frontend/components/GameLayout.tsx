import React from 'react';

interface GameLayoutProps {
    children: React.ReactNode;
    className?: string; // Allow passing classes for flexibility
}

export const GameLayout: React.FC<GameLayoutProps> = ({ children, className = '' }) => {
    return (
        <div className="relative w-full h-screen bg-[url('/react-py4web/static/build/assets/premium_wood_texture.png')] bg-cover bg-center flex items-center justify-center overflow-hidden">
            {/* Desktop Background (Visible only on larger screens) */}
            <div className="hidden md:block absolute inset-0 opacity-40pointer-events-none"
                style={{
                    backgroundImage: `url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%239C92AC' fill-opacity='0.1'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")`,
                }}
            />

            {/* Mobile App Container 
          - Mobile: Full width/height (100%)
          - Desktop: Fixed max-width (480px), rounded corners, shadow
      */}
            <div
                className={`
          relative 
          w-full h-full 
          md:w-[480px] md:h-[92vh] md:max-h-[920px] 
          md:rounded-[40px] 
          md:shadow-[0_20px_50px_rgba(0,0,0,0.5),0_0_0_12px_#1a1a1a] 
          bg-[#F5F3EF] 
          overflow-hidden 
          flex flex-col
          ${className}
        `}
            >


                {/* Main Content Area */}
                <div className="flex-1 w-full h-full relative overflow-hidden">
                    {children}
                </div>
            </div>
        </div>
    );
};

export default GameLayout;
