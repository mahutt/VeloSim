/**
 * MIT License
 *
 * Copyright (c) 2025 VeloSim Contributors
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */

import { Gauge, FileSliders } from 'lucide-react';
import { Link } from 'react-router';
import {
  SidebarGroup,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from '~/components/ui/sidebar';
import { useFeature } from '~/hooks/use-feature';
import usePreferences from '~/hooks/use-preferences';
import type { TranslationSchema } from '~/lib/i18n';

const mainNavItems = [
  {
    title: (t: TranslationSchema) => t.nav.simulations,
    url: '/simulations',
    icon: Gauge,
  },
  {
    title: (t: TranslationSchema) => t.nav.scenarios,
    url: '/',
    icon: FileSliders,
  },
] satisfies Array<{
  title: (t: TranslationSchema) => string;
  url: string;
  icon: typeof Gauge;
}>;

export function NavMain() {
  const showSimulations = useFeature('simulationsPage');
  const { t } = usePreferences();

  const items = mainNavItems.filter((i) => {
    if (i.url === '/simulations' && !showSimulations) return false;
    return true;
  });

  return (
    <SidebarGroup>
      <SidebarGroupLabel>{t.nav.section.main}</SidebarGroupLabel>
      <SidebarMenu>
        {items.map((item) => (
          <SidebarMenuItem key={item.url}>
            <SidebarMenuButton tooltip={item.title(t)} asChild>
              <Link to={item.url}>
                {item.icon && <item.icon />}
                <span>{item.title(t)}</span>
              </Link>
            </SidebarMenuButton>
          </SidebarMenuItem>
        ))}
      </SidebarMenu>
    </SidebarGroup>
  );
}
