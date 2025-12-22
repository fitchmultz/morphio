import React from 'react';

// Mock implementation for lucide-react icons
const createIconMock = (name) => {
  const Icon = (props) => {
    return React.createElement('svg', {
      ...props,
      'data-testid': `lucide-${name}`,
      width: 24,
      height: 24,
    });
  };
  return Icon;
};

// Export mocked icons used in the app
export const Moon = createIconMock('moon');
export const Sun = createIconMock('sun');
export const ChevronDown = createIconMock('chevron-down');
export const ChevronUp = createIconMock('chevron-up');
export const Menu = createIconMock('menu');
export const X = createIconMock('x');
export const Settings = createIconMock('settings');
export const User = createIconMock('user');
export const LogOut = createIconMock('log-out');
export const Home = createIconMock('home');
export const Check = createIconMock('check');
export const AlertCircle = createIconMock('alert-circle');
export const Loader = createIconMock('loader');
