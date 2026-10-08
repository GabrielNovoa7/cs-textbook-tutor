import { resourceUrl } from "./desktop";
import { useState } from "react";

export default function BookCover({ id, title }: { id: number; title: string }) {
  const [failed, setFailed] = useState(false);
  return <div className="book-cover">
    {failed ? <span className="cover-unavailable">📖<small>Preview unavailable</small></span>
      : <img src={resourceUrl(`/textbooks/${id}/cover`)} alt={`${title} cover`}
          loading="lazy" decoding="async" onError={() => setFailed(true)} />}
  </div>;
}
