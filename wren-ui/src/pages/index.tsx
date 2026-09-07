import { useEffect } from 'react';
import { useRouter } from 'next/router';
import { Path } from '@/utils/enum';
import PageLoading from '@/components/PageLoading';

export default function Index() {
  const router = useRouter();

  useEffect(() => {
    router.replace(Path.Home);
  }, [router]);

  return <PageLoading visible />;
}
