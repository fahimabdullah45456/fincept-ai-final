import {describe,it,expect} from 'vitest';
import {passwordRules,validateSignUp,validateSignIn,type SignUpValues} from './validation';
const valid:SignUpValues={full_name:'Demo User',email:'demo@example.com',password:'Fincept!2026',confirm_password:'Fincept!2026',accepted_terms:true};
describe('Authentication validation',()=>{
 it('accepts valid registration',()=>expect(validateSignUp(valid)).toEqual({}));
 it('requires all sign-up fields',()=>expect(Object.keys(validateSignUp({full_name:'',email:'',password:'',confirm_password:'',accepted_terms:false}))).toHaveLength(5));
 it('rejects invalid email',()=>expect(validateSignUp({...valid,email:'invalid'}).email).toBeTruthy());
 it('rejects password mismatch',()=>expect(validateSignUp({...valid,confirm_password:'different'}).confirm_password).toBeTruthy());
 it('requires terms',()=>expect(validateSignUp({...valid,accepted_terms:false}).accepted_terms).toBeTruthy());
 it('enforces all password rules',()=>{for(const password of ['short','lowercase!1','UPPERCASE!1','NoNumbers!','NoSymbols12'])expect(validateSignUp({...valid,password}).password).toBeTruthy();});
 it('updates password strength rather than fixing it',()=>{expect(passwordRules('').filter(r=>r.met)).toHaveLength(0);expect(passwordRules('a').filter(r=>r.met)).toHaveLength(0);expect(passwordRules('Ab1!').filter(r=>r.met)).toHaveLength(3);expect(passwordRules(valid.password).every(r=>r.met)).toBe(true);});
 it('does not enforce registration policy on existing sign-in credentials',()=>expect(validateSignIn({email:'demo@example.com',password:'old',remember:false})).toEqual({}));
});
