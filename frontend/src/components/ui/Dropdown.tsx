import React, { useState, useRef, useEffect } from 'react';
import { createPortal } from 'react-dom';

export interface DropdownItem {
  key: string;
  label: string;
  icon?: React.ReactNode;
  onClick: () => void;
  variant?: 'default' | 'danger';
  disabled?: boolean;
}

export interface DropdownProps {
  trigger: React.ReactNode;
  items: DropdownItem[];
  align?: 'left' | 'right';
  className?: string;
}

export const Dropdown: React.FC<DropdownProps> = ({
  trigger,
  items,
  align = 'right',
  className = ''
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [focusedIndex, setFocusedIndex] = useState(-1);
  const triggerRef = useRef<HTMLDivElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  // Close on click outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        triggerRef.current &&
        menuRef.current &&
        !triggerRef.current.contains(event.target as Node) &&
        !menuRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [isOpen]);

  // Keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!isOpen) return;

      switch (e.key) {
        case 'Escape':
          setIsOpen(false);
          setFocusedIndex(-1);
          break;
        case 'ArrowDown':
          e.preventDefault();
          setFocusedIndex((prev) => (prev + 1) % items.length);
          break;
        case 'ArrowUp':
          e.preventDefault();
          setFocusedIndex((prev) => (prev - 1 + items.length) % items.length);
          break;
        case 'Enter':
          e.preventDefault();
          if (focusedIndex >= 0 && !items[focusedIndex].disabled) {
            items[focusedIndex].onClick();
            setIsOpen(false);
            setFocusedIndex(-1);
          }
          break;
      }
    };

    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown);
      return () => document.removeEventListener('keydown', handleKeyDown);
    }
  }, [isOpen, focusedIndex, items]);

  const handleTriggerClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    setIsOpen(!isOpen);
    setFocusedIndex(-1);
  };

  const handleItemClick = (item: DropdownItem) => {
    if (item.disabled) return;
    item.onClick();
    setIsOpen(false);
    setFocusedIndex(-1);
  };

  const getMenuPosition = () => {
    if (!triggerRef.current) return { top: 0, left: 0 };

    const rect = triggerRef.current.getBoundingClientRect();
    const menuWidth = 200; // Approximate menu width

    return {
      top: rect.bottom + 8,
      left: align === 'right' ? rect.right - menuWidth : rect.left
    };
  };

  const menuPosition = getMenuPosition();

  return (
    <div className={`relative inline-block ${className}`}>
      {/* Trigger */}
      <div ref={triggerRef} onClick={handleTriggerClick}>
        {trigger}
      </div>

      {/* Menu */}
      {isOpen &&
        createPortal(
          <div
            ref={menuRef}
            className="fixed z-[1000] w-48 bg-slate-700/90 backdrop-blur-xl border border-slate-600/50 rounded-lg shadow-xl overflow-hidden"
            style={{
              top: `${menuPosition.top}px`,
              left: `${menuPosition.left}px`
            }}
            role="menu"
            aria-orientation="vertical"
          >
            {items.map((item, index) => (
              <button
                key={item.key}
                onClick={(e) => {
                  e.stopPropagation();
                  handleItemClick(item);
                }}
                disabled={item.disabled}
                className={`
                  w-full text-left px-4 py-2.5 text-sm transition-colors duration-200 flex items-center space-x-2
                  ${item.variant === 'danger' ? 'text-red-400 hover:bg-red-500/20' : 'text-white hover:bg-slate-600/50'}
                  ${item.disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
                  ${focusedIndex === index ? 'bg-slate-600/50' : ''}
                `}
                role="menuitem"
                aria-disabled={item.disabled}
              >
                {item.icon && <span className="flex-shrink-0">{item.icon}</span>}
                <span>{item.label}</span>
              </button>
            ))}
          </div>,
          document.body
        )}
    </div>
  );
};
