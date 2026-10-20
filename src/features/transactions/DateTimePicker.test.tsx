import {render,screen,within,fireEvent} from '@testing-library/react';
import {describe,it,expect,vi,beforeAll} from 'vitest';
import {DateTimePicker} from './DateTimePicker';
// jsdom does not implement the browser's top-layer Popover API.
beforeAll(()=>{HTMLElement.prototype.showPopover=function(){this.setAttribute('data-open','');};HTMLElement.prototype.hidePopover=function(){this.removeAttribute('data-open');};});
function setup(date='2026-10-19'){const onChange=vi.fn(),onTimeChange=vi.fn();render(<DateTimePicker value={date} time="17:48" onChange={onChange} onTimeChange={onTimeChange}/>);fireEvent.click(screen.getByRole('button',{name:'Date'}));return {onChange,onTimeChange,popup:screen.getByRole('dialog',{name:'Date calendar'})};}
describe('Figma calendar',()=>{
 it('renders Monday-first days and applies only after confirmation',()=>{const {onChange,onTimeChange,popup}=setup();expect(within(popup).getAllByRole('columnheader')[0]).toHaveAccessibleName('Monday');fireEvent.click(within(popup).getByRole('button',{name:'Tuesday, October 20, 2026'}));expect(onChange).not.toHaveBeenCalled();fireEvent.click(within(popup).getByRole('button',{name:'Apply'}));expect(onChange).toHaveBeenCalledWith('2026-10-20');expect(onTimeChange).toHaveBeenCalledWith('17:48');});
 it('navigates months and leap days correctly',()=>{const {popup}=setup('2028-02-29');expect(within(popup).getByRole('button',{name:'Tuesday, February 29, 2028'})).toBeInTheDocument();fireEvent.click(within(popup).getByRole('button',{name:'Next month'}));expect(within(popup).getByRole('button',{name:'Wednesday, March 1, 2028'})).toBeInTheDocument();});
 it('supports arrow and page keys across month boundaries',()=>{const {popup}=setup('2026-10-31');fireEvent.keyDown(within(popup).getByRole('button',{name:'Saturday, October 31, 2026'}),{key:'ArrowRight'});expect(within(popup).getByRole('gridcell',{selected:true})).toHaveTextContent('1');expect(within(popup).getByRole('button',{name:'Sunday, November 1, 2026'})).toHaveAttribute('tabindex','0');});
 it('rejects invalid 24-hour times without applying',()=>{const {onChange,popup}=setup();fireEvent.change(within(popup).getByLabelText('Time · 24-hour'),{target:{value:'25:99'}});fireEvent.click(within(popup).getByRole('button',{name:'Apply'}));expect(within(popup).getByRole('alert')).toHaveTextContent('valid 24-hour time');expect(onChange).not.toHaveBeenCalled();});
 it('disables browsing before the supported date boundary',()=>{const {popup}=setup('1901-01-01');expect(within(popup).getByRole('button',{name:'Previous month'})).toBeDisabled();});
});
