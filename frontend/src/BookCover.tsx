import { useState } from "react";

export default function BookCover({ id, title }: { id: number; title: string }) {
  const [failed, setFailed] = useState(false);
  return <div className="book-cover">
    {failed ? <span className="cover-unavailable">📖<small>Preview unavailable</small></span>
      : <img src={`http://127.0.0.1:8000/textbooks/${id}/cover`} alt={`${title} cover`}
          loading="lazy" decoding="async" onError={() => setFailed(true)} />}
  </div>;
}
