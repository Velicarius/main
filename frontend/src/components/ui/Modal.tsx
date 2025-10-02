import React, { useEffect, useRef } from 'react';
import { createPortal } from 'react-dom';

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
  closeOnOverlay?: boolean;
  className?: string;
}

export const Modal: React.FC<ModalProps> = ({
  isOpen,
  onClose,
  title,
  children,
  closeOnOverlay = true,
  className = '',
}) => {
  const modalRef = useRef<HTMLDivElement>(null);

  // Блокировка скролла страницы при открытии модалки
  useEffect(() => {
    if (isOpen) {
      const originalOverflow = document.body.style.overflow;
      document.body.style.overflow = 'hidden';
      
      return () => {
        document.body.style.overflow = originalOverflow;
      };
    }
  }, [isOpen]);

  // Обработка Escape
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
      return () => document.removeEventListener('keydown', handleEscape);
    }
  }, [isOpen, onClose]);

  // Фокус на первый интерактивный элемент при открытии
  useEffect(() => {
    if (isOpen && modalRef.current) {
      const firstInput = modalRef.current.querySelector('input, button, [tabindex]:not([tabindex="-1"])') as HTMLElement;
      if (firstInput) {
        firstInput.focus();
      }
    }
  }, [isOpen]);

  // Портал рендерится в document.body
  if (!isOpen) return null;

  const modalContent = (
    <div className="fixed inset-0 z-[1100]">
      {/* Overlay */}
      <div 
        className="fixed inset-0 bg-black/50"
        onClick={closeOnOverlay ? onClose : undefined}
      />
      
      {/* Modal Content */}
      <div className="fixed inset-0 z-[1101] flex items-center justify-center p-4">
        <div 
          ref={modalRef}
          className={`w-full max-w-[680px] rounded-2xl bg-slate-900 border border-white/10 shadow-2xl ${className}`}
          role="dialog"
          aria-modal="true"
          aria-labelledby="modal-title"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="flex items-center justify-between p-6 border-b border-white/10">
            <h2 id="modal-title" className="text-2xl font-bold text-white">
              {title}
            </h2>
            <button
              onClick={onClose}
              className="text-slate-400 hover:text-white transition-colors p-1"
              aria-label="Close modal"
            >
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Content */}
          <div className="p-6">
            {children}
          </div>
        </div>
      </div>
    </div>
  );

  // Рендер через портал в document.body
  return createPortal(modalContent, document.body);
};


