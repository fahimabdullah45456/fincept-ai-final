/** Small bounded rational parser: decimal arithmetic, no eval/Function or binary rounding. */
type Fraction={n:bigint;d:bigint};
const LIMIT=10_000_000_000_000;
export function calculate(expression:string):number {
 const input=expression.replace(/×/g,'*').replace(/÷/g,'/').replace(/−/g,'-').replace(/\s/g,'');
 if(!input||input.length>160||!/^[\d.+\-*/()%]+$/.test(input))throw Error('Enter a valid amount or calculation.');
 const tokens=input.match(/\d*\.?\d+|[.+\-*/()%]/g)||[];let index=0,depth=0;
 const check=(x:Fraction):Fraction=>{if(x.d===0n)throw Error('Cannot divide by zero.');if(x.n.toString().length>180||x.d.toString().length>180)throw Error('Calculation is too large.');return x;};
 const add=(a:Fraction,b:Fraction,minus=false)=>check({n:a.n*b.d+(minus?-1n:1n)*b.n*a.d,d:a.d*b.d});
 function atom():Fraction {if(++depth>24)throw Error('Too many nested parentheses.');let x:Fraction;const t=tokens[index++];if(t==='+'||t==='-'){x=atom();if(t==='-')x={...x,n:-x.n};}else if(t==='('){x=sum();if(tokens[index++]!==')')throw Error('Close the parentheses.');}else if(t&&/^\d*\.?\d+$/.test(t)){const [whole,decimal='']=t.split('.');if(decimal.length>12)throw Error('Use no more than 12 decimal places.');x={n:BigInt((whole||'0')+decimal),d:10n**BigInt(decimal.length)};}else throw Error('Complete the calculation first.');while(tokens[index]==='%'){index++;x=check({n:x.n,d:x.d*100n});}depth--;return x;}
 function product():Fraction {let x=atom();while(tokens[index]==='*'||tokens[index]==='/'){const op=tokens[index++],b=atom();x=check(op==='*'?{n:x.n*b.n,d:x.d*b.d}:{n:x.n*b.d,d:x.d*b.n});}return x;}
 function sum():Fraction {let x=product();while(tokens[index]==='+'||tokens[index]==='-'){const op=tokens[index++];x=add(x,product(),op==='-');}return x;}
 const x=sum();if(index!==tokens.length)throw Error('Check the calculation.');const sign=(x.n<0n)!==(x.d<0n)?-1:1,n=x.n<0n?-x.n:x.n,d=x.d<0n?-x.d:x.d;const minor=Number((n*100n*2n+d)/(d*2n))*sign;
 if(!Number.isSafeInteger(minor)||Math.abs(minor)>LIMIT)throw Error('Amount is too large.');return minor;
}
export type AmountDraft={expression:string;amountMinor:number|null;status:'empty'|'ready'|'pending'|'error';error?:string};
export function draft(expression=''):AmountDraft {if(!expression)return {expression,amountMinor:null,status:'empty'};if(/^\d*\.?\d+$/.test(expression)){try{return {expression,amountMinor:calculate(expression),status:'ready'};}catch(e){return {expression,amountMinor:null,status:'error',error:(e as Error).message};}}return {expression,amountMinor:null,status:'pending'};}
export type AmountAction={type:'type';value:string}|{type:'evaluate'}|{type:'quick';minor:number};
export function amountReducer(s:AmountDraft,a:AmountAction):AmountDraft {
 if(a.type==='type')return draft(a.value.slice(0,160));
 if(a.type==='quick'){if(s.status==='pending'||s.status==='error')return {...s,error:'Finish or clear the calculation before using quick amounts.'};const value=(s.amountMinor||0)+a.minor;return draft((value/100).toFixed(2));}
 try{const minor=calculate(s.expression);return {...draft((minor/100).toFixed(2)),amountMinor:minor};}catch(e){return {...s,amountMinor:null,status:'error',error:(e as Error).message};}
}
