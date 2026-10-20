import {createContext,useCallback,useContext,useEffect,useState,type ReactNode} from 'react';
import {ApiError,authApi,type User} from './services/authApi';
import type {SignInValues,SignUpValues} from './validation';
type AuthState={updateUser:(user:User)=>void;user:User|null;loading:boolean;sessionError:string;refresh:()=>Promise<void>;signIn:(v:SignInValues)=>Promise<void>;signUp:(v:SignUpValues)=>Promise<void>;signOut:()=>Promise<void>};
const Context=createContext<AuthState|null>(null);
export function AuthProvider({children}:{children:ReactNode}){
 const [user,setUser]=useState<User|null>(null);const [loading,setLoading]=useState(true);const [sessionError,setSessionError]=useState('');
 const refresh=useCallback(async()=>{setLoading(true);setSessionError('');try{setUser((await authApi.me()).user);}catch(e){setUser(null);if(!(e instanceof ApiError&&e.status===401))setSessionError(e instanceof Error?e.message:'Session could not be checked.');}finally{setLoading(false);}},[]);
 useEffect(()=>{void refresh();},[refresh]);
 useEffect(()=>{const recheck=()=>{if(document.visibilityState==='visible')void refresh();};document.addEventListener('visibilitychange',recheck);return()=>document.removeEventListener('visibilitychange',recheck);},[refresh]);
 const signIn=async(v:SignInValues)=>{setUser((await authApi.login(v)).user);setSessionError('');};
 const signUp=async(v:SignUpValues)=>{setUser((await authApi.register(v)).user);setSessionError('');};
 const signOut=async()=>{await authApi.logout();setUser(null);};
 return <Context.Provider value={{updateUser:setUser,user,loading,sessionError,refresh,signIn,signUp,signOut}}>{children}</Context.Provider>;
}
export function useAuth(){const c=useContext(Context);if(!c)throw new Error('AuthProvider is missing');return c;}
