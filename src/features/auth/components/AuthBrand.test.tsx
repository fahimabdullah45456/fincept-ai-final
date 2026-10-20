import {render,screen} from '@testing-library/react';
import {expect,it} from 'vitest';
import {AuthBrand} from './AuthBrand';
import {AuthFinancialIllustration} from './AuthFinancialIllustration';
it('renders the original SVG mark and a live text wordmark',()=>{
  const {container}=render(<AuthBrand/>);
  expect(screen.getByText('FINCEPT').tagName).toBe('SPAN');
  expect(container.querySelector('img')).toHaveAttribute('src','/assets/auth/logo-mark.svg');
});
it('composes the illustration from live text, original SVGs and ring geometry',()=>{
  const {container}=render(<AuthFinancialIllustration/>);
  expect(screen.getByText('৳8,450')).toBeVisible();
  for(const text of ['Housing','Emergency fund','Groceries','Illustrative demo values — not real financial data.']) expect(screen.getByText(text)).toBeVisible();
  const images=Array.from(container.querySelectorAll('img'));
  expect(images).toHaveLength(4);
  expect(images.every(image=>image.getAttribute('src')?.endsWith('.svg'))).toBe(true);
  expect(container.querySelectorAll('svg circle')).toHaveLength(2);
  expect(container.querySelector('img[src$=".png"]')).toBeNull();
});
