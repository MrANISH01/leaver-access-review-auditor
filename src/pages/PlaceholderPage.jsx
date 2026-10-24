import PageHeader from '../components/PageHeader.jsx'
import Card from '../components/Card.jsx'
import { EmptyState } from '../components/States.jsx'

export default function PlaceholderPage({ item }) {
  return (
    <>
      <PageHeader title={item.title} description={item.blurb} />
      <Card>
        <EmptyState
          icon={item.icon}
          title="This screen is built in a later milestone"
          text={`Planned for Milestone ${item.milestone}. Navigation and layout already work.`}
        />
      </Card>
    </>
  )
}
