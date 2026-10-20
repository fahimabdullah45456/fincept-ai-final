import {render,screen} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {expect,it} from 'vitest';
import {PasswordField,PasswordStrength,PrimaryButton} from './FormControls';
it('toggles password visibility without submitting',async()=>{const user=userEvent.setup();render(<PasswordField label="Password" name="password" defaultValue="secret"/>);const input=screen.getByLabelText('Password');expect(input).toHaveAttribute('type','password');await user.click(screen.getByRole('button',{name:'Show password'}));expect(input).toHaveAttribute('type','text');await user.click(screen.getByRole('button',{name:'Hide password'}));expect(input).toHaveAttribute('type','password');});
it('announces dynamic strength',()=>{const {rerender}=render(<PasswordStrength value=""/>);expect(screen.getByRole('status')).toHaveTextContent('Start typing');rerender(<PasswordStrength value="Fincept!2026"/>);expect(screen.getByRole('status')).toHaveTextContent('Requirements met');});
it('disables submission and shows loading',()=>{render(<PrimaryButton loading>Sign in</PrimaryButton>);expect(screen.getByRole('button')).toBeDisabled();expect(screen.getByRole('button')).toHaveTextContent('Please wait');});
