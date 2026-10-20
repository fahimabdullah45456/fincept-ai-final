import {Link,useSearchParams} from 'react-router-dom';
/** Real route destinations; unfinished features are never presented as implemented. */
export function SegmentPlaceholder({name}: {name: string}) {
  const [params]=useSearchParams();
  return <section className="segment-placeholder" aria-labelledby="segment-title">
    <span className="segment-eyebrow">Application foundation</span>
    <h1 id="segment-title">{name}</h1>
    <p>{name === 'Overview' ? 'Your Overview dashboard is not implemented in this project yet.' : `The ${name} segment is not implemented yet.`} The shared navigation is ready; financial features will be connected in their own segments.</p>
    {params.get('intent')&&<p>This {params.get('intent')} flow is not connected yet. No records have been changed.</p>}<Link to="/overview">Back to Overview</Link><br/><Link to="/auth/complete">Account and sign out</Link>
  </section>;
}
