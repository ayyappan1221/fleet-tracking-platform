import { Link } from 'react-router-dom';

export default function NotFound() {
  return (
    <div className='notfound-wrap'>
      <div className='panel notfound-card'>
        <p className='code'>404</p>
        <h1>Page not found</h1>
        <p>That link does not match any page in the fleet app.</p>
        <Link to='/' className='btn'>
          Back to dashboard
        </Link>
      </div>
    </div>
  );
}
